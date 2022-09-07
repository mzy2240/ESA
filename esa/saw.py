"""saw is short for SimAuto Wrapper. This module provides a class,
SAW, for interfacing with PowerWorld's Simulator Automation Server
(SimAuto). In addition to the SAW class, there are a few custom error
classes, such as PowerWorldError.

PowrWorld's documentation for SimAuto can be found
`here
<https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/Simulator_Automation_Server.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7C_____1>`__
"""

import locale
import logging
import warnings
import os
from pathlib import Path, PureWindowsPath
from typing import Union, List, Tuple
import re
import datetime
import json
from toolz.itertoolz import partition_all

import math
import numpy as np
from numpy.linalg import multi_dot, det, solve, inv
import numba as nb
import pandas as pd
from scipy.sparse import csr_matrix, coo_matrix, hstack, vstack
import scipy.sparse.linalg
import scipy
import networkx as nx
from tqdm import trange
import pythoncom
import win32com
from win32com.client import VARIANT
import tempfile

# Import corresponding AOT/JIT functions
import platform
PYTHON_VERSION = platform.python_version_tuple()
if PYTHON_VERSION[1] in ['7', '8', '9']:  # pragma: no cover
    try:
        exec(f"from .performance{PYTHON_VERSION[0]}{PYTHON_VERSION[1]} import initialize_bound, calculate_bound")
    except ImportError or RuntimeError:
        warnings.warn("Fail to load ahead-of-time compiled module. Downgrade to just-in-time module for compatibility.")
        from ._performance_jit import initialize_bound, calculate_bound
else:  # pragma: no cover
    from ._performance_jit import initialize_bound, calculate_bound


# Before doing anything else, set up the locale. The docs note this is
# not thread safe, and should thus be done right away.
locale.setlocale(locale.LC_ALL, '')

# TODO: Make logging more configurable.
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%H:%M:%S"
)

# Listing of PowerWorld data types. I guess 'real' means float?
DATA_TYPES = ['Integer', 'Real', 'String']
# Hard-code based on indices.
NUMERIC_TYPES = DATA_TYPES[:2]
NON_NUMERIC_TYPES = DATA_TYPES[-1]

# RequestBuildDate uses Delphi conventions, which counts days since
# Dec. 30th, 1899.
DAY_0 = datetime.date(year=1899, month=12, day=30)


# noinspection PyPep8Naming
class SAW(object):
    """A SimAuto Wrapper in Python"""

    # Class level property defining the fields which will be returned
    # for different ObjectTypes by the get_power_flow_results method.
    POWER_FLOW_FIELDS = {
        'bus': ['BusNum', 'BusName', 'BusPUVolt', 'BusAngle', 'BusNetMW',
                'BusNetMVR'],
        'gen': ['BusNum', 'GenID', 'GenMW', 'GenMVR'],
        'load': ['BusNum', 'LoadID', 'LoadMW', 'LoadMVR'],
        'shunt': ['BusNum', 'ShuntID', 'ShuntMW', 'ShuntMVR'],
        'branch': ['BusNum', 'BusNum:1', 'LineCircuit', 'LineMW',
                   'LineMW:1', 'LineMVR', 'LineMVR:1']
    }

    # Class level property defining the columns used by the DataFrame
    FIELD_LIST_COLUMNS = \
        ['key_field', 'internal_field_name', 'field_data_type', 'description',
         'display_name']

    # Older versions of Simulator omit the "display name" field.
    FIELD_LIST_COLUMNS_OLD = FIELD_LIST_COLUMNS[0:-1]

    # Latest versions (V22 Nov and V23) introduce new field "enterable"
    FIELD_LIST_COLUMNS_NEW = \
        ['key_field', 'internal_field_name', 'field_data_type', 'description',
         'display_name', 'enterable']

    # Class level property defining columns used for
    # GetSpecificFieldList method.
    SPECIFIC_FIELD_LIST_COLUMNS = \
        ['variablename:location', 'field', 'column header',
         'field description']

    SPECIFIC_FIELD_LIST_COLUMNS_NEW = \
        ['variablename:location', 'field', 'column header',
         'field description', 'enterable']

    # SimAuto properties that we allow users to set via the
    # set_simauto_property method.
    SIMAUTO_PROPERTIES = {'CreateIfNotFound': bool, 'CurrentDir': str,
                          'UIVisible': bool}

    def __init__(self, FileName, early_bind=False, UIVisible=False,
                 object_field_lookup=('bus', 'gen', 'load', 'shunt',
                                      'branch'),
                 CreateIfNotFound=False, pw_order=False):
        """Initialize SimAuto wrapper. The case will be opened, and
        object fields given in object_field_lookup will be retrieved.

        :param FileName: Full file path to .pwb file to open. This will
            be passed to the SimAuto function OpenCase.
        :param early_bind: Whether (True) or not (False) to connect to
            SimAuto via early binding.
        :param UIVisible: Whether or not to display the PowerWorld UI.
        :param CreateIfNotFound: Set CreateIfNotFound = True if objects
            that are updated through the ChangeParameters functions
            should be created if they do not already exist in the case.
            Objects that already exist will be updated.
            Set CreateIfNotFound = False to not create new objects
            and only update existing ones.
        :param object_field_lookup: Listing of PowerWorld objects to
            initially look up available fields for. Objects not
            specified for lookup here will be looked up later as
            necessary.
        :param pw_order: Set pw_order = True if you want to have exact
            same order as shown in PW Simulator. Default is False, which
            generally sorts the data in a bus ascending order.

        Note that
        `Microsoft recommends
        <https://docs.microsoft.com/en-us/office/troubleshoot/office-developer/binding-type-available-to-automation-clients>`__
        early binding in most cases.
        """
        # Initialize logger.
        self.log = logging.getLogger(self.__class__.__name__)

        # Set the decimal delimiter based on this PC's locale.
        locale_db = locale.localeconv()
        self.decimal_delimiter = locale_db['decimal_point']

        # Useful reference for early vs. late binding:
        # https://docs.microsoft.com/en-us/office/troubleshoot/office-developer/binding-type-available-to-automation-clients
        #
        # Useful reference for early and late binding in pywin32:
        # https://youtu.be/xPtp8qFAHuA
        try:
            if early_bind:
                try:
                    # Use early binding.
                    self._pwcom = win32com.client.gencache.EnsureDispatch(
                        'pwrworld.SimulatorAuto')
                except AttributeError:
                    # Use late binding.
                    self._pwcom = win32com.client.dynamic.Dispatch(
                        'pwrworld.SimulatorAuto')
            else:
                # Use late binding.
                self._pwcom = win32com.client.dynamic.Dispatch(
                    'pwrworld.SimulatorAuto')
        except Exception as e:
            m = ("Unable to launch SimAuto. ",
                 "Please confirm that your PowerWorld license includes "
                 "the SimAuto add-on, and that SimAuto has been "
                 "successfully installed.")
            self.log.exception(m)

            raise e

        # Initialize self.pwb_file_path. It will be set in the OpenCase
        # method.
        self.pwb_file_path = None
        # Set the CreateIfNotFound and UIVisible properties.
        self.set_simauto_property('CreateIfNotFound', CreateIfNotFound)
        self.set_simauto_property('UIVisible', UIVisible)
        # Set the pw_order property.
        self.pw_order = pw_order

        # Prepare an empty auxiliary file used for updating the UI.
        self.ntf = tempfile.NamedTemporaryFile(mode='w', suffix='.axd',
                                               delete=False)
        self.empty_aux = Path(self.ntf.name).as_posix()
        self.ntf.close()

        # Open the case.
        self.OpenCase(FileName=FileName)

        # Get the version number and the build date
        version_string, self.build_date = self.get_version_and_builddate()
        self.version = int(re.search(r'\d+', version_string)[0])

        # Sensitivity-related initialization
        self.lodf = None

        # Look up and cache field listing and key fields for the given
        # object types in object_field_lookup.
        self._object_fields = {}
        self._object_key_fields = {}

        for obj in object_field_lookup:
            # Always use lower case.
            o = obj.lower()

            # Get the field listing. This will store the resulting
            # field list in self._object_fields[o].
            self.GetFieldList(o)

            # Get the key fields for this object. This will store the
            # results in self._object_key_fields[o]
            self.get_key_fields_for_object_type(ObjectType=o)

    ####################################################################
    # Helper Functions
    ####################################################################
    def change_and_confirm_params_multiple_element(self, ObjectType: str,
                                                   command_df: pd.DataFrame) \
            -> None:
        """Change parameters for multiple objects of the same type, and
        confirm that the change was respected by PowerWorld.

        :param ObjectType: The type of objects you are changing
            parameters for.
        :param command_df: Pandas DataFrame representing the objects
            which will have their parameters changed. The columns should
            be object field variable names, and MUST include the key
            fields for the given ObjectType (which you can get via the
            get_key_fields_for_object_type method). Columns which are
            not key fields indicate parameters to be changed, while the
            key fields are used internally by PowerWorld to look up
            objects. Each row of the DataFrame represents a single
            element.

        :raises CommandNotRespectedError: if PowerWorld does not
            actually change the parameters.
        :raises: PowerWorldError: if PowerWorld reports an error.

        :returns: None
        """
        # Start by cleaning up the DataFrame. This will avoid silly
        # issues later (e.g. comparing ' 1 ' and '1').
        cleaned_df = self._change_parameters_multiple_element_df(
            ObjectType=ObjectType, command_df=command_df)

        # Now, query for the given parameters.
        df = self.GetParametersMultipleElement(
            ObjectType=ObjectType, ParamList=cleaned_df.columns.tolist())

        # Check to see if the two DataFrames are equivalent.
        eq = self._df_equiv_subset_of_other(df1=cleaned_df, df2=df,
                                            ObjectType=ObjectType)

        # If DataFrames are not equivalent, raise a
        # CommandNotRespectedError.
        if not eq:
            m = ('After calling ChangeParametersMultipleElement, not all '
                 'parameters were actually changed within PowerWorld. Try '
                 'again with a different parameter (e.g. use GenVoltSet '
                 'instead of GenRegPUVolt).')
            raise CommandNotRespectedError(m)

        # All done.
        return None

    def change_parameters_multiple_element_df(
            self, ObjectType: str, command_df: pd.DataFrame) -> None:
        """Helper to call ChangeParametersMultipleElement, but uses a
        DataFrame to determine parameters and values. This method is
        lighter weight but perhaps "riskier" than the
        "change_and_confirm_params_multiple_element" method, as no
        effort is made to ensure PowerWorld respected the given command.

        :param ObjectType: The type of objects you are changing
            parameters for.
        :param command_df: Pandas DataFrame representing the objects
            which will have their parameters changed. The columns should
            be object field variable names, and MUST include the key
            fields for the given ObjectType (which you can get via the
            get_key_fields_for_object_type method). Columns which are
            not key fields indicate parameters to be changed, while the
            key fields are used internally by PowerWorld to look up
            objects. Each row of the DataFrame represents a single
            element.
        """
        # Simply call the helper function.
        self._change_parameters_multiple_element_df(
            ObjectType=ObjectType, command_df=command_df)

    def clean_df_or_series(self, obj: Union[pd.DataFrame, pd.Series],
                           ObjectType: str) -> Union[pd.DataFrame, pd.Series]:
        """Helper to cast data to the correct types, clean up strings,
        and sort DataFrame by BusNum (if applicable/present).

        :param obj: DataFrame or Series to clean up. It's assumed that
            the object came more or less directly from placing results
            from calling SimAuto into a DataFrame or Series. This means
            all data will be strings (even if they should be numeric)
            and data which should be strings often have unnecessary
            white space. If obj is a DataFrame (Series), the columns
            (index) must be existing fields for the given object type
            (i.e. are present in the 'internal_field_name' column of the
            corresponding DataFrame which comes from calling
            GetFieldList for the given object type).
        :param ObjectType: Object type the data in the DataFrame relates
            to. E.g. 'gen'

        :raises ValueError: if the DataFrame (Series) columns (index)
            are not valid fields for the given object type.

        :raises TypeError: if the input 'obj' is not a DataFrame or
            Series.
        """
        # Get the type of the obj.
        if isinstance(obj, pd.DataFrame):
            df_flag = True
            fields = obj.columns.to_numpy()
        elif isinstance(obj, pd.Series):
            df_flag = False
            fields = obj.index.to_numpy()
        else:
            raise TypeError('The given object is not a DataFrame or '
                            'Series!')

        # Do not sort if pw_order = True
        if not self.pw_order:
            self._clean_df(ObjectType, fields, obj, df_flag)
        return obj

    def _clean_df(self, ObjectType, fields, obj, df_flag):
        # Determine which types are numeric.
        numeric = self.identify_numeric_fields(ObjectType=ObjectType,
                                               fields=fields)
        numeric_fields = fields[numeric]

        # Make the numeric fields, well, numeric.
        obj[numeric_fields] = self._to_numeric(obj[numeric_fields])

        # Now handle the non-numeric cols.
        nn_cols = fields[~numeric]

        # Start by ensuring the non-numeric columns are indeed strings.
        obj[nn_cols] = obj[nn_cols].astype(str)

            # Here we'll strip off the white space.
        obj[nn_cols] = obj[nn_cols].apply(lambda x: x.str.strip()) if df_flag else obj[nn_cols].str.strip()

        # Sort by BusNum if present.
        if df_flag:
            try:
                obj.sort_values(by='BusNum', axis=0, inplace=True)
            except KeyError:
                # If there's no BusNum don't sort the DataFrame.
                pass
            else:
                # Re-index with simple monotonically increasing values.
                obj.index = np.arange(start=0, stop=obj.shape[0])

    def exit(self):
        """Clean up for the PowerWorld COM object"""
        # Clean the empty aux file
        os.unlink(self.ntf.name)
        # Close the case and delete the COM object
        self.CloseCase()
        del self._pwcom
        self._pwcom = None
        return None

    def get_key_fields_for_object_type(self, ObjectType: str) -> pd.DataFrame:
        """Helper function to get all key fields for an object type.

        :param ObjectType: The type of the object to get key fields for.

        :returns: DataFrame with the following columns:
            'internal_field_name', 'field_data_type', 'description', and
            'display_name'. The DataFrame will be indexed based on the key
            field returned by the Simulator, but modified to be 0-based.

        This method uses the GetFieldList function, documented
        `here
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/GetFieldList_Function.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Functions%7C_____14>`__.

        It's also worth looking at the key fields documentation
        `here
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/Key_Fields.htm>`__.
        """
        # Cast to lower case.
        obj_type = ObjectType.lower()

        # See if we've already looked up the key fields for this object.
        # If we have, just return the cached results.
        try:
            key_field_df = self._object_key_fields[obj_type]
        except KeyError:
            # We haven't looked up key fields for this object yet.
            pass
        else:
            # There's not work to do here. Return the DataFrame.
            return key_field_df

        # Get the listing of fields for this object type.
        field_list = self.GetFieldList(ObjectType=obj_type, copy=False)

        # Here's what I've gathered:
        # Key fields will be of the format *<number><letter>*
        #   where the <letter> part is optional. It seems the
        #   letter is only listed for the last key field.
        # Required fields are indicated with '**'.
        # There are also fields of the form *<letter>* and these
        #   seem to be composite fields? E.g. 'BusName_NomVolt'.

        # Extract key fields.
        key_field_mask = \
            field_list['key_field'].str.match(r'\*[0-9]+[A-Z]*\*').to_numpy()
        # Making a copy isn't egregious here because there are a
        # limited number of key fields, so this will be a small frame.
        key_field_df = field_list.loc[key_field_mask].copy()

        # Replace '*' with the empty string.
        key_field_df['key_field'] = \
            key_field_df['key_field'].str.replace(r'\*', '', regex=True)

        # Remove letters.
        key_field_df['key_field'] = \
            key_field_df['key_field'].str.replace('[A-Z]*', '', regex=True)

        # Get numeric, 0-based index.
        # noinspection PyTypeChecker
        key_field_df['key_field_index'] = \
            self._to_numeric(key_field_df['key_field']) - 1

        # Drop the key_field column (we only wanted to convert to an
        # index).
        key_field_df.drop('key_field', axis=1, inplace=True)

        # Use the key_field_index for the DataFrame index.
        key_field_df.set_index(keys='key_field_index', drop=True,
                               verify_integrity=True, inplace=True)

        # Sort the index.
        key_field_df.sort_index(axis=0, inplace=True)

        # Ensure the index is as expected (0, 1, 2, 3, etc.)
        assert np.array_equal(
            key_field_df.index.to_numpy(),
            np.arange(0, key_field_df.index.to_numpy()[-1] + 1))

        # Track for later.
        self._object_key_fields[obj_type] = key_field_df

        return key_field_df

    def get_key_field_list(self, ObjectType: str) -> List[str]:
        """Convenience function to get a list of key fields for a given
        object type.

        :param ObjectType: PowerWorld object type for which you would
            like a list of key fields. E.g. 'gen'.

        :returns: List of key fields for the given object type. E.g.
            ['BusNum', 'GenID']
        """
        # Lower case only.
        obj_type = ObjectType.lower()

        # Attempt to get the key field DataFrame from our cached
        # dictionary.
        try:
            key_field_df = self._object_key_fields[obj_type]
        except KeyError:
            # DataFrame isn't cached. Get it.
            key_field_df = self.get_key_fields_for_object_type(obj_type)

        # Return a listing of the internal field name.
        return key_field_df['internal_field_name'].tolist()

    def get_power_flow_results(self, ObjectType: str, additional_fields: Union[
        None, List[str]] = None) -> Union[None, pd.DataFrame]:
        """Get the power flow results from SimAuto server.

        :param ObjectType: Object type to get results for. Valid types
            are the keys in the POWER_FLOW_FIELDS class attribute (case
            insensitive).

        :param additional_fields: Pass a list of field names to extend
            the default attributes in the POWER_FLOW_FIELDS.

        :returns: Pandas DataFrame with the corresponding results, or
            None if the given ObjectType is not present in the model.

        :raises ValueError: if given ObjectType is invalid.
        """
        object_type = ObjectType.lower()
        # Get the listing of fields for this object type.
        try:
            field_list = self.POWER_FLOW_FIELDS[object_type]
            if additional_fields:
                # Make a copy of the field list.
                field_list = field_list[:]
                # Extend it.
                field_list += additional_fields
        except KeyError as e:
            raise ValueError(f'Unsupported ObjectType for power flow results, {ObjectType}.') from e



        return self.GetParametersMultipleElement(ObjectType=object_type,
                                                 ParamList=field_list)

    def get_version_and_builddate(self) -> tuple:
        return self._call_simauto(
            "GetParametersSingleElement",
            "PowerWorldSession",
            convert_list_to_variant(["Version", "ExeBuildDate"]),
            convert_list_to_variant(["", ""]))

    def identify_numeric_fields(self, ObjectType: str,
                                fields: Union[List, np.ndarray]) -> np.ndarray:
        """Helper which looks up PowerWorld internal field names to
        determine if they're numeric (True) or not (False).

        :param ObjectType: Type of object for which we're identifying
            numeric fields. E.g. "Branch" or "gen"
        :param fields: List of PowerWorld internal fields names for
            which we're identifying if they are or aren't numeric.
            E.g. ['BusNum', 'BusNum:1', 'LineCircuit', 'LineStatus']

        :returns: Numpy boolean array indicating which of the given
            fields are numeric. Going along with the example given for
            "fields": np.array([True, True, False, False])
        """
        # Start by getting the field list for this ObjectType. Note
        # that in most cases this will be cached and thus be quite
        # fast. If it isn't cached now, it will be after calling this.
        field_list = self.GetFieldList(ObjectType=ObjectType, copy=False)

        # Rely on the fact that the field_list is already sorted by
        # internal_field_name to get indices related to the given
        # internal field names.
        # fields = list(fields)
        idx = field_list['internal_field_name'].to_numpy().searchsorted(fields)

        # Ensure the columns are actually in the field_list. This is
        # necessary because search sorted gives the index of where the
        # given values would go, and doesn't guarantee the values are
        # actually present. However, we want to use searchsorted for its
        # speed and leverage the fact that our field_list DataFrame is
        # already sorted.
        try:
            # ifn for "internal_field_name."
            ifn = field_list['internal_field_name'].to_numpy()[idx]

            # Ensure given fields are present in the field list.
            if set(ifn) != set(fields):
                raise ValueError('The given object has fields which do not'
                                 ' match a PowerWorld internal field name!')
        except IndexError as e:
            # An index error also indicates failure.
            raise ValueError('The given object has fields which do not' ' match a PowerWorld internal field name!') from e


        # Now extract the corresponding data types.
        data_types = field_list['field_data_type'].to_numpy()[idx]

        # Determine which types are numeric and return.
        return np.isin(data_types, NUMERIC_TYPES)

    def set_simauto_property(self, property_name: str,
                             property_value: Union[str, bool]):
        """Set a SimAuto property, e.g. CreateIfNotFound. The currently
        supported properties are listed in the SAW.SIMAUTO_PROPERTIES
        class constant.

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/Simulator_Automation_Server_Properties.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Properties%7C_____1>`__

        :param property_name: Name of the property to set, e.g.
            UIVisible.
        :param property_value: Value to set the property to, e.g. False.
        """
        # Ensure the given property name is valid.
        if property_name not in self.SIMAUTO_PROPERTIES:
            raise ValueError(f'The given property_name, {property_name}, is not currently supported. Valid properties are: {list(self.SIMAUTO_PROPERTIES.keys())}')


        # Ensure the given property value has a valid type.
        # noinspection PyTypeHints
        if not isinstance(property_value,
                          self.SIMAUTO_PROPERTIES[property_name]):
            m = f'The given property_value, {property_value}, is invalid. It must be of type {self.SIMAUTO_PROPERTIES[property_name]}.'

            raise ValueError(m)

        # If we're setting CurrentDir, ensure the path is valid.
        # It seems PowerWorld does not check this.
        if property_name == 'CurrentDir' and not os.path.isdir(property_value):
            raise ValueError(f'The given path for CurrentDir, {property_value}, is not a valid path!')


        # Set the property.
        try:
            self._set_simauto_property(property_name=property_name,
                                       property_value=property_value)
        except AttributeError as e:
            if property_name == 'UIVisible':
                self.log.warning(
                    'UIVisible attribute could not be set. Note this SimAuto '
                    'property was not introduced until Simulator version 20. '
                    'Check your version with the get_simulator_version method.'
                )
            else:
                raise e from None

    def get_ybus(self, full: bool = False, file: Union[str, None] = None) -> Union[np.ndarray, csr_matrix]:
        """Helper to obtain the YBus matrix from PowerWorld (in Matlab sparse
        matrix format) and then convert to scipy csr_matrix by default.
        :param full: Convert the csr_matrix to the numpy array (full matrix).
        :param file: Path to the external Ybus file.
        """
        if file:
            _tempfile_path = file
        else:
            _tempfile = tempfile.NamedTemporaryFile(mode='w', suffix='.mat',
                                                    delete=False)
            _tempfile_path = Path(_tempfile.name).as_posix()
            _tempfile.close()
            cmd = f'SaveYbusInMatlabFormat("{_tempfile_path}", NO)'
            self.RunScriptCommand(cmd)
        with open(_tempfile_path, 'r') as f:
            f.readline()
            mat_str = f.read()
        mat_str = re.sub(r'\s', '', mat_str)
        lines = re.split(';', mat_str)
        ie = r'[0-9]+'
        fe = r'-*[0-9]+\.[0-9]+'
        dr = re.compile(r'(?:Ybus)=(?:sparse\()({ie})'.format(ie=ie))
        exp = re.compile(
            r'(?:Ybus\()({ie}),({ie})(?:\)=)({fe})(?:\+j\*)(?:\()({fe})'.format(
                ie=ie, fe=fe))
        # Get the dimension from the first line in lines
        dim = dr.match(lines[0])[1]
        n = int(dim)
        row = []
        col = []
        data = []
        for line in lines[1:]:
            match = exp.match(line)
            if match is None:
                continue
            idx1, idx2, real, imag = match.groups()
            # Type conversion can be optimized to provide slightly
            # improvement
            admittance = float(real) + 1j * float(imag)
            row.append(int(idx1))
            col.append(int(idx2))
            data.append(admittance)
        # The row index is always in the ascending order in the mat file
        sparse_matrix = csr_matrix(
            (data, (np.asarray(row) - 1, np.asarray(col) - 1)), shape=(n, n),
            dtype=complex)
        return sparse_matrix.toarray() if full else sparse_matrix

    def get_branch_admittance(self):
        """Helper function to get the branch admittance matrix, usually known as
        Yf and Yt.
        :returns: A Yf sparse matrix and a Yt sparse matrix
        """
        key = self.get_key_field_list('bus')
        df = self.GetParametersMultipleElement('bus', key)

        branch = self.GetParametersMultipleElement('branch', self.get_key_field_list('branch') + ['LineR', 'LineX', 'LineC',
                                                                                              'LineTap', 'LinePhase'])
        branch['LineR'] = branch['LineR'].astype(float)
        branch['LineX'] = branch['LineX'].astype(float)
        branch['LineC'] = branch['LineC'].astype(float)
        branch['LineTap'] = branch['LineTap'].astype(float)
        branch['LinePhase'] = branch['LinePhase'].astype(float)

        nb = df.shape[0]
        nl = branch.shape[0]

        Ys = 1 / (branch['LineR'].to_numpy() + 1j * branch['LineX'].to_numpy())  # series admittance
        Bc = branch['LineC'].to_numpy()  # line charging susceptance
        tap = branch['LineTap'].to_numpy()
        shift = branch['LinePhase'].to_numpy()
        tap = tap * np.exp(1j * np.pi / 180 * shift)
        Ytt = Ys + 1j * Bc / 2
        Yff = Ytt / (tap * np.conj(tap))
        Yft = - Ys / np.conj(tap)
        Ytf = - Ys / tap

        # lookup table for formatting bus numbers
        def loop_translate(a, d):
            n = np.ndarray(a.shape, dtype=int)
            for k in d:
                n[a == k] = d[k]
            return n

        d = dict()
        for index, value in df['BusNum'].items():
            d[value] = index
        f = branch['BusNum'].to_numpy(dtype=int).reshape(-1)
        f = loop_translate(f, d)
        t = branch['BusNum:1'].to_numpy(dtype=int).reshape(-1)
        t = loop_translate(t, d)
        ## connection matrix for line & from buses
        i = np.r_[range(nl), range(nl)]  ## double set of row indices
        Yf = csr_matrix((np.hstack([Yff.reshape(-1), Yft.reshape(-1)]), (i, np.hstack([f, t]))), (nl, nb))
        Yt = csr_matrix((np.hstack([Ytf.reshape(-1), Ytt.reshape(-1)]), (i, np.hstack([f, t]))), (nl, nb))
        return Yf, Yt

    def get_shunt_admittance(self):
        """Get shunt admittance Ysh.
        :return: A Ysh sparse matrix
        """
        base = self.GetParametersMultipleElement('Sim_Solution_Options', ['SBase']).to_numpy(float).ravel()
        key = self.get_key_field_list('bus')
        df = self.GetParametersMultipleElement('bus', key + ['BusSS', 'BusSSMW'])
        df['BusSS'] = df['BusSS'].astype(float)
        df['BusSSMW'] = df['BusSSMW'].astype(float)
        df.fillna(0, inplace=True)
        return (df['BusSSMW'].to_numpy() + 1j * df['BusSS'].to_numpy()) / base

    def get_jacobian(self, full=False):
        """Helper function to get the Jacobian matrix, by default return a
        scipy sparse matrix in the csr format
        :param full: Convert the csr_matrix to the numpy array (full matrix).
        """
        jacfile = tempfile.NamedTemporaryFile(mode='w', suffix='.m',
                                              delete=False)
        jacfile_path = Path(jacfile.name).as_posix()
        jacfile.close()
        jidfile = tempfile.NamedTemporaryFile(mode='w', delete=False)
        jidfile_path = Path(jidfile.name).as_posix()
        jidfile.close()
        cmd = f'SaveJacobian("{jacfile_path}","{jidfile_path}",M,R);'
        self.RunScriptCommand(cmd)
        with open(jacfile_path, 'r') as f:
            mat_str = f.read()
        os.unlink(jacfile.name)
        os.unlink(jidfile.name)
        mat_str = re.sub(r'\s', '', mat_str)
        lines = re.split(';', mat_str)
        ie = r'[0-9]+'
        fe = r'-*[0-9]+\.[0-9]+'
        dr = re.compile(r'(?:Jac)=(?:sparse\()({ie})'.format(ie=ie))
        exp = re.compile(
            r'(?:Jac\()({ie}),({ie})(?:\)=)({fe})'.format(
                ie=ie, fe=fe))
        row = []
        col = []
        data = []
        # Get the dimension from the first line in lines
        dim = dr.match(lines[0])[1]
        n = int(dim)
        for line in lines[1:]:
            match = exp.match(line)
            if match is None:
                continue
            idx1, idx2, real = match.groups()
            row.append(int(idx1))
            col.append(int(idx2))
            data.append(float(real))
        sparse_matrix = csr_matrix(
            (data, (np.asarray(row) - 1, np.asarray(col) - 1)), shape=(n, n))
        return sparse_matrix.toarray() if full else sparse_matrix

    def to_graph(self, node: str = 'bus', geographic: bool = False,
                 directed: bool = False, node_attr=None, edge_attr=None) \
            -> Union[nx.MultiGraph, nx.MultiDiGraph]:
        """Generate the graph network model (NetworkX) from the topology.
        Currently supports the bus-level topology and the inter-substation
        level topology. Parallel lines (if exist) are preserved in the
        model.
        :param edge_attr:  A valid field name(str) or iterable of
        field names that are used to retrieve values and add them to the
        graph as edge attributes. All fields belonging to object branch are
        available.
        :param node_attr: A valid field name(str) or iterable of
        field names that are used to retrieve values and add them to the
        graph as node attributes. All fields belonging to the node type are
        available.
        :param directed: Whether to convert to a directed graph (based on
        the direction of real power flow).
        :param geographic: Include latitude and longitude in the node's
        attributes. If geographic information is unavailable in the case,
        the latitude and the longitude will be NaN.
        :param node: Elements to be represented by nodes. Only 'bus' or
        'substation' is supported.
        """
        if node not in ['bus', 'substation']:
            raise ValueError(
                "Currently only support 'bus' or 'substation' as the node "
                "type.")
        qf = []
        nf = []
        node_from = None
        node_to = None
        if node == 'bus':
            qf = self.get_key_field_list('branch') + ['LineMW']
            node_from = "BusNum"
            node_to = "BusNum:1"
            nf = ['BusNum']
            if geographic:
                nf += ['Latitude:1', 'Longitude:1']
        elif node == 'substation':
            qf = self.get_key_field_list('branch') + ['SubNum', 'SubNum:1',
                                                      'LineMW']
            node_from = "SubNum"
            node_to = "SubNum:1"
            nf = ['SubNum']
            if geographic:
                nf += ['Latitude', 'Longitude']
        if edge_attr:
            if isinstance(edge_attr, (list, tuple)):
                qf.extend(edge_attr)
            else:
                qf.append(edge_attr)
                edge_attr = [edge_attr]
        try:
            branch_df = self.GetParametersMultipleElement('branch', qf)
        except ValueError as e:
            raise e
        if directed:
            graph_type = nx.MultiDiGraph
            for index, row in branch_df.iterrows():
                linemw = row['LineMW']
                if linemw < 0:
                    original_from = row[node_from]
                    original_to = row[node_to]
                    branch_df.loc[index, 'LineMW'] = abs(linemw)
                    branch_df.loc[index, node_from] = original_to
                    branch_df.loc[index, node_to] = original_from
        else:
            graph_type = nx.MultiGraph
        graph = nx.from_pandas_edgelist(branch_df, node_from, node_to,
                                        create_using=graph_type,
                                        edge_key="LineCircuit",
                                        edge_attr=edge_attr)
        if node == "substation":
            graph.remove_edges_from(nx.selfloop_edges(graph))
        if node_attr:
            if isinstance(node_attr, (list, tuple)):
                nf.extend(node_attr)
            else:
                nf.append(node_attr)
        if geographic or node_attr:
            try:
                node_df = self.GetParametersMultipleElement(node, nf)
                node_attr_reformat = node_df.set_index(node_from).to_dict('index')
                nx.set_node_attributes(graph, node_attr_reformat)
            except ValueError as e:
                raise e
        return graph

    def get_lodf_matrix(self, precision: int = 3):
        """Obtain LODF matrix in numpy array or scipy sparse matrix.
        By default, it obtains the lodf matrix directly from PW. If size
        is larger than 1000, then precision will be applied to filter out
        small values and the result will be returned in scipy sparse matrix.

        :param precision:  number of decimal to keep.

        :returns: LODF matrix
        """
        self.pw_order = True
        count = self.ListOfDevices('branch').shape[0]
        self.RunScriptCommand("CalculateLODFMatrix(OUTAGES,ALL,ALL,YES,DC,ALL,YES)")
        array = [f"LODFMult:{x}" for x in range(count)]
        if count <= 1000:
            self._extracted_from_get_lodf_matrix_9(array)
        else:
            self._extracted_from_get_lodf_matrix_16(array, precision)
        return self.lodf, self.isl

    # TODO Rename this here and in `get_lodf_matrix`
    def _extracted_from_get_lodf_matrix_16(self, array, precision):
        container = []
        isl = None
        for batch in partition_all(20, array):
            df = self.GetParametersMultipleElement('branch', batch)
            temp = df.to_numpy(dtype=float) / 100
            temp = temp.round(precision)
            isl = np.any(temp >= 10, axis=1) if isl is None else np.logical_or(isl, np.any(temp >= 10, axis=1))

            temp[isl, :] = 0
            temp = coo_matrix(temp)
            temp.eliminate_zeros()
            container.append(temp)
        temp = hstack(container).tolil()
        temp[isl, :] = 0
        temp[isl, isl] = -1
        temp = temp.tocsr()
        temp.eliminate_zeros()
        self.lodf = temp
        self.isl = isl

    # TODO Rename this here and in `get_lodf_matrix`
    def _extracted_from_get_lodf_matrix_9(self, array):
        df = self.GetParametersMultipleElement('branch', array)
        temp = df.to_numpy(dtype=float)/100
        self.isl = np.any(temp >= 10, axis=1)
        temp[self.isl, :] = 0
        temp[self.isl, self.isl] = -1
        self.lodf = temp

    def get_incidence_matrix(self):
        """
        Obtain the incidence matrix.

        :returns: Incidence matrix
        """
        branch = self.ListOfDevices("branch")
        bus = self.ListOfDevices("bus")
        incidence = np.zeros([branch.shape[0], bus.shape[0]], dtype=int)

        for i, row in branch.iterrows():
            incidence[i, row["BusNum"] - 1] = 1
            incidence[i, row["BusNum:1"] - 1] = -1
        return incidence

    def get_shift_factor_matrix(self, method: str = 'DC'):
        """
        Calculate the injection shift factor matrix using the auxiliary
        script CalculateShiftFactorsMultipleElement.

        :param method: The linear method to be used for the calculation. The
        options are AC, DC or DCPS.
        :returns: A dense float matrix in the numpy array format.
        """
        temp = self.pw_order
        self.pw_order = True
        key = self.get_key_field_list('branch')
        fields = key + ['Selected']
        df = self.GetParametersMultipleElement('branch', fields)
        num_branch = df.shape[0]
        df['Selected'] = 'YES'
        self.change_parameters_multiple_element_df('branch', df)
        # now run the calculation for all the seleced branches
        self.RunScriptCommand(f"CalculateShiftFactorsMultipleElement(BRANCH,SELECTED,BUYER,"
                              f"[SLACK],{method})")
        isf_fields = ['MultBusTLRSens']
        for i in range(1, num_branch):
            isf_fields += [f"MultBusTLRSens:{i}"]
        res = self.GetParametersMultipleElement('Bus', isf_fields).to_numpy(dtype=float)
        self.pw_order = temp
        return res


    def _prepare_sensitivity(self):
        """
        Prepare the matrix for sensitivity analysis.
        """
        temp = self.pw_order
        self.pw_order = True
        bus = self.GetParametersMultipleElement('bus', ['BusNum', 'BusCat'])
        br = self.GetParametersMultipleElement('branch', ['BusNum', 'BusNum:1', 'LineX'])
        self.pw_order = temp
        slack = bus[bus['BusCat'] == 'Slack'].index.tolist()[0]
        noslack = bus.index.tolist()
        noslack.remove(slack)
        bus.reset_index(inplace=True)
        bus.set_index('BusNum', inplace=True)
        f = br['BusNum'].map(bus['index']).to_numpy(dtype=int)
        t = br['BusNum:1'].map(bus['index']).to_numpy(dtype=int)
        nl = br.shape[0]
        nb = bus.shape[0]
        i = np.r_[range(nl), range(nl)]
        Cft = csr_matrix((np.r_[np.ones(nl), -np.ones(nl)], (i, np.r_[f, t])), (nl, nb))
        x_val = br['LineX'].to_numpy(dtype=float)
        b = 1 / x_val
        Bf = csr_matrix((np.r_[b, -b], (i, np.r_[f, t])))
        Bbus = Cft.T * Bf

        def get_data(ary: csr_matrix, first_zero=False):
            """
            This function takes in the csr matrix, extract the first row, returns zero like matrix.
            """
            _col = ary.getrow(0).toarray().nonzero()[1]  # get the non-zero col
            _row = np.zeros(ary[0].data.shape)  # change data to 0
            _data = _row
            if _col.size < _row.size:
                _col = np.insert(_col, 0, -1)
            elif first_zero:
                _data = np.insert(_row, 0, -1)  # replace the first data with -1
                _row = np.insert(_row, 0, 0)
                _col = np.insert(_col, 0, 0)
            return csr_matrix((_data, (_row, _col)), shape=ary[0].shape)  # create zero like csr
                                                                          # matrix

        v_Bbus = vstack([get_data(Bbus), Bbus[1:]], format='csr').T
        Bbus = vstack([get_data(v_Bbus, True), v_Bbus[1:]]).T

        return Bbus, Bf, Cft, slack, noslack


    def get_shift_factor_matrix_fast(self):
        """
        Calculate the injection shift factor matrix directly using the incidence
        matrix and the susceptance matrix. This method should be much faster than
        the PW script command for large cases.

        :returns: A dense float matrix in the numpy array format.
        """
        Bbus, Bf, _, _, _ = self._prepare_sensitivity()
        res = Bf * scipy.sparse.linalg.inv(Bbus)
        res[:, 0] = 0
        return res.T.todense()


    def get_ptdf_matrix_fast(self):
        """
        Calculate the power transfer distribution factor natively. This method should be much
        faster than the PW script command for large cases.

        :returns: A dense float matrix in the numpy array format.
        """
        Bbus, Bf, _, slack, noslack = self._prepare_sensitivity()
        n = Bbus.shape[0]
        noref = noslack
        dP = np.eye(n, n)

        # solve for change in voltage angles
        dTheta = np.zeros((n, n))
        Bref = Bbus[noslack, :][:, noref].tocsc()
        dtheta_ref = scipy.sparse.linalg.spsolve(Bref, dP[noslack, :])

        dTheta[noref, :] = dtheta_ref

        return Bf * dTheta


    def get_lodf_matrix_fast(self):
        """
        Calculate the line outage distribution factor natively. This method should be much
        faster than the PW script command for large cases.

        :returns: A dense float matrix in the numpy array format.
        """
        Bbus, Bf, Cft, slack, noslack = self._prepare_sensitivity()
        PTDF = self.get_ptdf_matrix_fast()
        H = PTDF * Cft.T
        numerical_zero = 1e-10

        nl, nb = PTDF.shape
        # this loop avoids the divisions by zero
        # in those cases the LODF column should be zero
        LODF = np.zeros((nl, nl))
        div = 1 - H.diagonal()
        islands = []
        for j in range(H.shape[1]):
            if abs(div[j]) > numerical_zero:
                LODF[:, j] = H[:, j] / div[j]
            else:
                islands.append(j)

        res = LODF - np.diag(np.diag(LODF)) - np.eye(nl, nl)
        return res.T


    def fast_n1_test(self):
        """
        A pure LODF-based fast N-1 contingency analysis implementation.

        :returns: A boolean value to indicate whether the system is N-1 secure.
        """
        LODF = self.get_lodf_matrix_fast()
        temp = LODF.copy()
        np.fill_diagonal(temp, 0)
        isl = np.invert(np.any(temp, axis=1))
        print(f"There are {np.sum(isl)} branches that could cause islanding.")
        original = self.pw_order
        self.pw_order = True
        br = self.GetParametersMultipleElement('branch', ['LineMW', 'LineLimMVA'])
        self.pw_order = original
        flows = br['LineMW'].to_numpy(dtype=float)
        limits = br['LineLimMVA'].to_numpy(dtype=float)
        limits[limits == 0] = np.inf
        post_flows = flows + LODF*flows
        res = np.invert(np.any(post_flows > limits, axis=0))
        secure = np.all(res)
        print("---------- Omitting the islanding cases ----------")
        print(f"N-1 secure: {secure}")
        return secure


    def fast_n2_islanding_detection(self):
        """
        Quickly identify the N-2 islanding CTGs using LODF

        returns: A tuple with the number of islanding CTGs and the islanding matrix
        """
        LODF = self.get_lodf_matrix_fast()
        nb = LODF.shape[0]
        tr = 1e-8
        c2_isl = np.zeros([nb, nb])
        qq = LODF * LODF.conj().T
        c2_isl[abs(qq - 1) <= tr] = 1  # use
        # tr for better numerical stability
        return (np.count_nonzero(c2_isl) - nb) / 2, c2_isl


    def change_to_temperature(self, T: Union[int, float, np.ndarray], R25=7.283, R75=8.688):
        """
        Change line resistance according to temperature.
        The default coefficients are from IEEE Std 738-2012.
        Note: The original case has to be set for 25 degree Celsius.

        :param T: Target temperature. If it is a single int or float, then a uniform temperature
            will be assigned to all the lines; If it is a numpy array, then you need to pass a
            2D array with first row being the index of branch and second row being the temperature.
        :param R25: Per unit resistance at 25 Celsius
        :param R75: Per unit resistance at 75 Celsius
        """
        branch = self.GetParametersMultipleElement('branch', self.get_key_field_list('branch') + ['LineR', 'BranchDeviceType'])
        if isinstance(T, np.ndarray):
            temp = np.full(branch.shape[0], 25, dtype=float)
            columns = T.shape[1]
            indexes = T[0, :].copy()
            indexes = indexes.astype(int).ravel()
            for i in range(columns):
                temp[indexes[i]] = T[1, i]
            branch['LineR'] = np.multiply(branch['LineR'], temp)
        else:
            branch.loc[branch['BranchDeviceType'] == "Line", "LineR"] *= (1 + (R75 / R25 - 1) / 50 * (T - 25))
        self.change_parameters_multiple_element_df('branch', branch)

    def run_contingency_analysis(self, option: str = "N-1", validate: bool = False):
        """ESA implementation of fast N-1 and N-2 contingency analysis.
        The case is expected to have a valid power flow state.
        Run SolvePowerFlow first if you are not sure.

        :param option: Choose between N-1 and N-2 mode
        :param validate: Use PW internal CA to validate the result. Default is False.

        :returns: A tuple of system security status (bool) and a matrix
            showing the result of contingency analysis (if exist)
        """
        self.set_simauto_property('CreateIfNotFound', True)
        self.pw_order = True
        validation_result = None

        df = self.GetParametersMultipleElement("branch", ['BusNum', 'BusNum:1', 'LineCircuit', 'MWFrom', 'LineLimMVA'])
        convert_dict = {'MWFrom': float,
                        'LineLimMVA': float
                        }
        df = df.astype(convert_dict)
        if np.any(df['LineLimMVA'] == 0):
            raise(Error("Branch without limit is detected. Please fix and try again."))
        if np.any((df['MWFrom'] > df['LineLimMVA'])):
            raise(Error("The current operational states has violations. Please fix and try again."))

        if self.lodf is None:
            self.lodf, self.isl = self.get_lodf_matrix()

        lim = df['LineLimMVA'].to_numpy().flatten()
        f = df['MWFrom'].to_numpy().flatten()
        # isl = np.any(self.lodf >= 10, axis=1)
        count = df.shape[0]
        c1_isl = np.zeros(count)
        c1_isl[self.isl] = 1
        secure, margins, ctg, violations = self.n1_fast(c1_isl, count, self.lodf, f, lim)
        result = ctg
        if option == 'N-2':
            if not secure:
                # Adjust line limits to eliminate N-1 contingencies
                lim = self.n1_protect(margins, violations, lim)
                df['LineLimMVA'] = pd.Series(lim)
                # Update the line limits in the case as well
                # Of course without saving it won't affect the original case
                self.change_parameters_multiple_element_df('branch', df)
            secure, result = self.n2_fast(c1_isl, count, self.lodf, f, lim)
        if validate and not secure:
            if option == 'N-1':
                f_result = df[result>0]
                ctg = pd.DataFrame()
                ctg_ele = pd.DataFrame()
                temp = 'BRANCH' + f_result['BusNum'] + f_result['BusNum:1'] + ' ' + f_result['LineCircuit']
                ctg['Name'] = temp
                ctg_ele['Contingency'] = temp
                ctg_ele['Object'] = temp
                ctg_ele['Action'] = 'OPEN'
            elif option == 'N-2':
                result_cleaned = result[~(result==0).all(1)]
                b0 = result_cleaned[:,0]
                b1 = result_cleaned[:,1]
                bf0 = df.iloc[b0, :].reset_index(drop=True)
                bf1 = df.iloc[b1, :].reset_index(drop=True)
                ctg = pd.DataFrame()
                ctg_ele0 = pd.DataFrame()
                ctg_ele1 = pd.DataFrame()
                temp = 'L' + bf0['BusNum'] + bf0['BusNum:1'] + ' ' + bf0['LineCircuit'] + bf1['BusNum'] + bf1[
                    'BusNum:1'] + ' ' + bf1['LineCircuit']
                ctg['Name'] = temp
                ctg_ele0['Contingency'] = temp
                ctg_ele0['Object'] = 'BRANCH' + bf0['BusNum'] + bf0['BusNum:1'] + ' ' + bf0['LineCircuit']
                ctg_ele0['Action'] = 'OPEN'
                ctg_ele1['Contingency'] = temp
                ctg_ele1['Object'] = 'BRANCH' + bf1['BusNum'] + bf1['BusNum:1'] + ' ' + bf1['LineCircuit']
                ctg_ele1['Action'] = 'OPEN'
                ctg_ele = pd.concat([ctg_ele0, ctg_ele1]).sort_index().reset_index(drop=True)
            self.change_parameters_multiple_element_df('Contingency', ctg)
            self.change_parameters_multiple_element_df('ContingencyElement', ctg_ele)
            validation_result = self.ctg_solveall()
        return secure, result, validation_result

    def run_robustness_analysis(self):
        """Compute the metric RCF to quantify the robustness of
        power grids against cascading failures. The RCF metric takes the
        operational states, the branch's capacities and the topological
        structure into account and gives an entropy-based value.
        The formula is given from the following paper:
        Koç, Yakup, Martijn Warnier, Robert E. Kooij, and Frances MT Brazier.
        "An entropy-based metric to quantify the robustness of power grids
        against cascading failures." Safety science 59 (2013): 126-134.

        :returns: The RCF value.
        """
        warnings.warn("Please make sure the current system state is valid")
        kf = self.get_key_field_list('branch') + ["LineMW", "LineMVA", "LineLimMVA",
                                                  "LineMaxPercent", "BranchDeviceType"]
        branch_df = self.GetParametersMultipleElement('branch', kf)
        if (branch_df['LineLimMVA'] == 0).all():
            warnings.warn("Line limits are missing or infinite")
        for index, row in branch_df.iterrows():
            linemw = row['LineMW']
            if linemw < 0:
                original_from = row['BusNum']
                original_to = row['BusNum:1']
                branch_df.loc[index, 'LineMW'] = abs(linemw)
                branch_df.loc[index, 'BusNum'] = original_to
                branch_df.loc[index, 'BusNum:1'] = original_from

        graph = nx.from_pandas_edgelist(branch_df, "BusNum", "BusNum:1",
                                        create_using=nx.MultiDiGraph, edge_key="LineCircuit",
                                        edge_attr=["LineMW", "LineLimMVA", "LineMaxPercent",
                                                   "BranchDeviceType"])
        for edge in graph.edges:
            out_node = edge[0]
            total = 0
            for out_edge in graph.out_edges(out_node, data='LineMW'):
                total += out_edge[2]
            if total == 0:
                total += 0.000001
            for key in list(graph[edge[0]][edge[1]].keys()):
                p = graph[edge[0]][edge[1]][key]['LineMW'] / float(
                    total)  # Assume no parallel lines
                graph[edge[0]][edge[1]][key]['p'] = p
                graph[edge[0]][edge[1]][key]['tolerance'] = 100 / (
                            graph[edge[0]][edge[1]][key]['LineMaxPercent'] + 0.000001)

        output_nodes = [u for u, deg in graph.out_degree() if deg]
        for node in output_nodes:
            H = 0
            nodal_robust = 0
            out_edge_copy = (None, None, None)
            for out_edge in graph.out_edges(node, data='p'):
                p = out_edge[2]
                if out_edge[0] == out_edge_copy[0] and out_edge[1] == out_edge_copy[1]:
                    tolerance = graph[out_edge[0]][out_edge[1]]['2'][
                        'tolerance']  # Assume no parallel lines
                else:
                    tolerance = graph[out_edge[0]][out_edge[1]]['1'][
                        'tolerance']  # Assume no parallel lines
                H += p * math.log(p + 1e-6, 10)  # Some p = 0, and assume the base is 10
                nodal_robust += tolerance * p * math.log(p + 1e-6, 10)
                out_edge_copy = out_edge
            graph.nodes[node]['H'] = H
            graph.nodes[node]['nodal_robust'] = -nodal_robust

        total_distribution = 0
        for node in output_nodes:
            for out_edge in graph.out_edges(node, data='LineMW'):
                total_distribution += out_edge[2]
        for node in output_nodes:
            node_dist = 0
            for out_edge in graph.out_edges(node, data='LineMW'):
                node_dist += out_edge[2]
            node_significance = node_dist / total_distribution
            graph.nodes[node]['node_significance'] = node_significance

        rcf = 0
        for node in output_nodes:
            rcf += graph.nodes[node]['nodal_robust'] * graph.nodes[node]['node_significance']

        return rcf

    def run_ecological_analysis(self, target: str = 'MW', split_generator: bool = True):
        """
        This method is leveraging applied ecological network analysis to quantify
        the varity of robustness of the power system.

        Reference:
        [1] H. Huang, Z. Mao, A. Layton and K. R. Davis, 
        "An Ecological Robustness Oriented Optimal Power Flow for Power Systems' Survivability,"
        in IEEE Transactions on Power Systems, doi: 10.1109/TPWRS.2022.3168226.
        [2] Panyam, V., Huang, H., Davis, K., & Layton, A. (2019).
        An ecosystem perspective for the design of sustainable power systems. Procedia Cirp, 80, 269-274.

        :param target: the real, reactive, and apparent power over the system. 
        The default value is MW, which is the real power
        Users can change to MVR, which is the reactive power; or MVA, which is the apparent power
        :param split_generator: Choose to split or aggregate multiple generators connected to one bus
        True: split generators, which considers the generators' robustness to the whole system
        False: aggregate generators, which doesn't consider generators' robustness 

        :results: it is a list of ecological metrics, including the Ecological Robustness (Reco), 
        the Ascendancy (ASC), the Development Capacity (DC), the Cycled Throughflow (tstc), the Finn Cycling Index (CI)
        and the Total System Overhead (TSO) 
        """
        warnings.warn("Please make sure the current system state is valid")

        # Collect power flow information from the case
        # ideally, allow users to choose whether they want to analyze real power (MW), reactive
        # power (MVR), or whole power (MVA)
        # one issue, losses don't have MVA
        kf = self.get_key_field_list('branch') + ["LineMW", "LineMVR", "LineMVA", "LineLossMW",
                                                  "LineLossMVR"]
        branch_df = self.GetParametersMultipleElement('branch', kf)
        # add a function to get LinelossMVA
        LinelossMVA = np.zeros(len(branch_df))
        for i in range(len(branch_df)):
            realloss = branch_df["LineLossMW"][i]
            reactiveloss = branch_df["LineLossMVR"][i]
            LinelossMVA[i] = np.sqrt(pow(realloss, 2)+pow(reactiveloss, 2))
        branch_df['LineLossMVA'] = LinelossMVA
        gen_keys = self.get_key_field_list('gen') + ["GenMW", "GenMVR", "GenMVA", "GenProdCost"]
        gen = self.GetParametersMultipleElement('gen', gen_keys)
        self.pw_order = False  # fix the order of generator list for later matrix organization
        load_keys = self.get_key_field_list('load')+["LoadMW", "LoadMVR", "LoadMVA"]
        load = self.GetParametersMultipleElement('load', load_keys)
        bus_keys = self.get_key_field_list('bus')
        bus = self.GetParametersMultipleElement('bus', bus_keys)

        if split_generator:
            # Option 2  -- the previous way to study the overall robustness,
            # It should be better since it captures the generators' robustness
            # not aggregate gen
            # gen_unique=list(set(gen.BusNum))
            num_gen = len(gen)
            num_bus = len(bus)
            num_actor = num_gen + num_bus + 3
            s = (num_actor, num_actor)
            EFM = np.zeros(s)

            # feed generator to first row
            for i in range(num_gen):
                    EFM[0][i+1] += gen.GenMW[i]  # [row][col]
            # feed generator to diagonal between Gen and Bus
            for i in range(num_bus):
                for j in range(num_gen):
                    if bus.BusNum[i] == gen.BusNum[j]:
                        EFM[j+1][1+num_gen+i] = EFM[0][j+1]
            # feed line flow to EFM
            for i in range(len(branch_df)):
                frombus = branch_df['BusNum'][i]
                tobus = branch_df['BusNum:1'][i]
                flow = branch_df['LineMW'][i]
            # f_index=bus['BusNum'].index[frombus-1]
            # t_index=bus['BusNum'].index[tobus-1] 
                if flow > 0:
                    EFM[frombus+num_gen][tobus+num_gen] += abs(flow)
                else:
                    EFM[tobus+num_gen][frombus+num_gen] += abs(flow)
            # feed loss
            for i in range(len(branch_df)):
                frombus = branch_df['BusNum'][i]
                tobus = branch_df['BusNum:1'][i]
                lossMW = branch_df['LineLossMW'][i]
                EFM[num_gen+frombus][2+num_bus+num_gen] += abs(lossMW)

        else:
            # Option 1 #### Not considering generators' robustness
            # aggregate gen
            gen_unique = list(set(gen.BusNum))
            num_gen = len(gen_unique)
            num_bus = bus.shape[0]
            num_actor = num_gen+num_bus+3
            s = (num_actor, num_actor)
            EFM = np.zeros(s)

            # feed generator to first row
            for i in range(num_gen):
                for j in range(len(gen)):
                    if gen_unique[i] == gen.BusNum[j]:
                        EFM[0][i+1] += gen.GenMW[j]  # [row][col]
            # feed generator to diagonal between Gen and Bus
            for i in range(num_bus):
                for j in range(num_gen):
                    if bus.BusNum[i] == gen_unique[j]:
                        EFM[j+1][1+num_gen+i] = EFM[0][j+1]
                        
            # feed load to last second
            for i in range(len(load)):
                for j in range(num_bus):
                    if load.BusNum[i] == bus.BusNum[j]:
                        EFM[1+num_gen+i][1+num_gen+num_bus] += load.LoadMW[i]
                        
            # feed line flow to EFM
            for i in range(len(branch_df)):
                frombus = branch_df['BusNum'][i]
                tobus = branch_df['BusNum:1'][i]
                flow = branch_df['LineMW'][i]
            # f_index=bus['BusNum'].index[frombus-1]
            # t_index=bus['BusNum'].index[tobus-1] 
                if flow > 0:
                    EFM[frombus+num_gen][tobus+num_gen] += abs(flow)
                else:
                    EFM[tobus+num_gen][frombus+num_gen] += abs(flow)
            # feed loss
            for i in range(len(branch_df)):
                frombus = branch_df['BusNum'][i]
                tobus = branch_df['BusNum:1'][i]
                lossMW = branch_df['LineLossMW'][i]
                EFM[num_gen+frombus][2+num_bus+num_gen] += abs(lossMW)

        # All ecological metrics
        T = EFM
        tstp = sum(T)

        k = 1  # coefficient variable
        P = T.transpose()
        # P_rsum=sum(P,dims=2) sum over row
        # P_csum=sum(P,dims=1) sum over columns

        P_csum = P.sum(axis=0)  # sum over colums
        P_rsum = P.sum(axis=1)  # sum over rows

        k = 1
        s = len(T)
        Q = np.zeros((s, s))

        tstp = T.sum()

        for i in range(len(T)):         
            if P_rsum[i] > 0:     
                Q[i] = P[i]/P_rsum[1]
                
        # N = inv(eye(size(P,1))-Q);  % Leontief's Inverse      
        N = np.linalg.inv(np.eye(s)-Q)

        inflow = T[0].sum()  # sum(T[1,:])

        internal_flow = sum(sum(T[1:s-2][1:s-2]))  # sum(sum(T[2:(s-2),2:(s-2)]));
            
        tstf = inflow + internal_flow    # total system throughflow (inflow + internal_flow)

        mpl = tstf/inflow                # mean path length   
            
        d_N = N.diagonal()                   # diagonal elements of the N matrix

        # c_re = (d_N[2:(n_T-2)]-ones(size(d_N[2:(n_T-2)]))) ./ d_N[2:(n_T-2)];  
        temp = d_N[1:s-2]
        temp1 = np.ones(s-3)
        c_re = (temp-temp1)/temp # cycling efficiency vector

        tstc = c_re.transpose()*P_rsum[1:s-2]  # cycled throughflow
            
        ci = tstc/tstf   # Finn Cycling Index (CI)
            
        AMI_ij = np.zeros((s, s))  # Average Mutual Information (AMI)
        T_csum = T.sum(axis=0)  # sum over colums
        T_rsum = T.sum(axis=1)  # sum over rows

        # i=1;    
        for i in range(len(T)):
            for j in range(len(T)):
                value = ((T[i][j]*tstp)/(T_rsum[i]*T_csum[j]))
                if value > 0:
                    AMI_ij[i][j] = (T[i][j]/tstp)*math.log(value, 2)
                else:
                    AMI_ij[i][j] = 0

        ami = sum(sum(AMI_ij))
        asc = ami * tstp  # Ascendency (ASC)

        DC_ij = np.zeros((s, s))  # Development Capacity (DC)
        for i in range(len(T)):
            for j in range(len(T)):
                value = T[i][j]/tstp
                if value > 0:
                    DC_ij[i][j] = T[i][j]*math.log(value, 2)
                else:
                    DC_ij[i][j] = 0
        dc = -1*sum(sum(DC_ij))
            
        tso = dc - asc  # Total System Overhead (TSO)

        reco = -1*k*(asc/dc)*math.log(asc/dc)  # Robustness (R)

        # Here are all ecosystems' metrics can be calculated
        # tstc: cycled throughflow
        # ci: Finn Cycling Index (CI)
        # tso: Total System Overhead (TSO)
        # asc: Ascendency (ASC)
        # dc:  Development Capacity (DC)
        # robustness: Reco
        return [reco, asc, dc, tstc, ci, tso]

    def n1_fast(self, c1_isl, count, lodf, f, lim):
        """ A modified fast N-1 method.

        :param c1_isl: Array of islanding lines
        :param count: Number of lines
        :param lodf: LODF matrix
        :param f: Flow on the lines
        :param lim: Array of line limits

        :returns: A tuple of N-1 status (bool) and the N-1 result (if exist)
        """
        ctg = np.zeros(count, dtype=int)
        violations = np.zeros(count, dtype=int)
        margins = np.zeros(count)
        for i in range(count):
            if c1_isl[i] == 0:
                flows = f + lodf[i, :] * f[i]
                qq = abs(flows) / lim
                violating_lines = abs(flows) > lim
                num_of_violations = np.sum(violating_lines)
                margins = np.maximum(margins, qq)
                if num_of_violations:
                    ctg[i] = 1
                    violations[violating_lines] += 1
        print(f"The size of N-1 islanding set is {np.sum(c1_isl)}")
        print(
            f"Fast N-1 analysis was performed, {np.sum(ctg)} dangerous N-1 contigencies were found, "
            f"{np.sum(violations > 0)} lines are violated")
        if np.sum(ctg):
            print(
                "Grid is not N-1 secure. Invoke n1_protect function to automatically increasing limits through lines.")
            return False, margins, ctg, violations
        else:
            print("Grid is N-1 secure.")
            return True, None, None, None

    def n1_protect(self, margins, lines, lim):
        """Adjust line limits to eliminate N-1 contingencies.

        :param margins: Array of line loading margins.
        :param lines: Array of number of line overloading contingencies.
        :param lim: Array of line limits.

        :return lim: Array of line limits after adjustment.
        """
        print("Automatically adjust line limits to achieve N-1 secure.")
        mm = margins[lines[:] == 0].max(0)
        lim[lines > 0] = margins[lines > 0] * lim[lines > 0] / mm
        return lim

    def n2_fast(self, c1_isl, count, lodf, f, lim):
        """A modified fast N-2 method.

        :param c1_isl: Array of islanding lines
        :param count: Number of lines
        :param lodf: LODF matrix
        :param f: Flow on the lines
        :param lim: Array of line limits

        :returns: A tuple of N-2 status (bool) and the N-2 result (if exist)
        """
        print("Start fast N-2 analysis")
        c2_isl = np.zeros([count, count])
        A0 = np.ones([count, count]) - np.eye(count)
        B0 = np.ones([count, count])
        A = np.zeros([count, count])
        denominator = np.ones([count, count])
        numerator = np.ones([count, count])
        tr = 1e-8
        A0[c1_isl == 1, :] = 0
        A0[:, c1_isl == 1] = 0
        A0[abs(f) < tr, :] = 0
        A0[:, abs(f) < tr] = 0
        qq = lodf * (lodf.conj().T)
        A0[abs(qq - 1) <= tr] = 0
        c2_isl[abs(qq - 1) <= tr] = 1
        print("Size of C2_isl is", (np.sum(c2_isl.ravel()) - count) / 2)
        denominator -= lodf * (lodf.conj().T)
        numerator += multi_dot([np.diag(1 / f), lodf, np.diag(f)])
        A[A0.nonzero()] = numerator[A0.nonzero()] / denominator[A0.nonzero()]
        bp = multi_dot([np.diag(1 / (lim - f)), lodf, np.diag(f)])
        bn = multi_dot([-np.diag(1 / (lim + f)), lodf, np.diag(f)])
        bn -= np.diag(np.diag(bn))
        bp -= np.diag(np.diag(bp))
        B0 -= np.diag(np.diag(B0))
        k = 0
        changing = 1
        num_isl_ctg = np.sum(c1_isl.ravel()) * count - np.sum(c1_isl.ravel()) + np.sum(c2_isl.ravel()) / 2
        kmax = 10
        storage = {}

        while changing == 1 and k < kmax:
            oldA = np.sum(A0.ravel())
            oldB = np.sum(B0.ravel())
            print(
                f"{k} iteration: number of potential contingencies::{oldA / 2: <10}, B::{oldB: <10}; Islanding "
                f"contingencies: {num_isl_ctg: <10}")

            # PHASE I
            # Wbuf1 = np.maximum(np.diag(bp.max(0)) @ A, np.diag(bp.min(0)) @ A)
            # Wbuf2 = np.maximum(np.diag(bn.max(0)) @ A, np.diag(bn.min(0)) @ A)
            # W = np.maximum(Wbuf1 + Wbuf1.conj().T, Wbuf2 + Wbuf2.conj().T)
            W, Wbuf1, Wbuf2 = initialize_bound(bp.max(0), bp.min(0), bn.max(0), bn.min(0), A)

            storage[k + 1, 1] = A0
            storage[k + 1, 2] = B0
            storage[k + 1, 6] = W
            storage[k + 1, 3] = A
            storage[k + 1, 4] = bp
            storage[k + 1, 5] = bn
            A0[W <= 1] = 0
            A[A0 == 0] = 0

            # PHASE II
            Amax0 = A.max(0)
            Amin0 = A.min(0)
            Amax1 = A.max(1)
            Amin1 = A.min(1)
            Wbuf1 = np.maximum(np.outer(bp.max(1), Amax0), np.outer(bp.min(1), Amin0))
            Wbuf2 = np.maximum(np.outer(bn.max(1), Amax0), np.outer(bn.min(1), Amin0))
            # Wb1 = np.maximum(bp @ np.diag(Amax1) + Wbuf1, bp @ np.diag(Amin1) + Wbuf1)
            # Wb2 = np.maximum(bn @ np.diag(Amax1) + Wbuf2, bn @ np.diag(Amin1) + Wbuf2)
            # W = np.maximum(Wb1, Wb2)  # bounding matrix for the set B
            W = calculate_bound(bp, bn, Amax1, Amin1, Wbuf1, Wbuf2)
            storage[k + 1, 7] = W
            B0[W <= 1] = 0
            bn[B0 == 0] = 0
            bp[B0 == 0] = 0
            k = k + 1
            if oldA == np.sum(A0.ravel()) and oldB == np.sum(B0.ravel()):
                changing = 0
        secure, result = self.n2_bruteforce(count, A0, lodf, lim, f)
        return secure, result

    def n2_bruteforce(self, count, A0, lodf, lim, f):
        """ Bruteforce for fast N-2 method

        :param count: number of branches
        :param A0: filtered contingencies
        :param lodf: LODF matrix
        :param lim: branch limits
        :param f: branch flow

        :returns: Security status and detailed results
        """

        @nb.njit(fastmath=True)
        def compute_violation_numba(lodf, f, c2, lim, i, count, A0, brute_cont, idx):  # pragma: no cover
            for j in range(i + 1, count):
                if A0[i, j]:
                    temp1 = lodf[i, i] * lodf[j, j]
                    temp2 = lodf[i, j] * lodf[j, i]
                    det = temp1 - temp2
                    if det == 0:
                        c2[i,j] = 1
                        c2[j,i] = 1
                    else:
                        length = len(f)
                        num = 0
                        f_new = np.zeros(length)
                        temp3 = lodf[j, j] * f[i] - lodf[i, j] * f[j]
                        temp4 = lodf[i, i] * f[j] - lodf[j, i] * f[i]
                        xq_0 = temp3 / det
                        xq_1 = temp4 / det
                        for k in range(length):
                            temp5 = lodf[k, i] * xq_0
                            temp6 = lodf[k, j] * xq_1
                            f_new[k] = f[k] - temp5 - temp6
                            if abs(f_new[k]) > lim[k]:
                                num = num + 1
                        if f_new[i] > lim[i]:
                            num = num - 1
                        if f_new[j] > lim[j]:
                            num = num - 1
                        if num > 0:
                            brute_cont[idx, 0] = i
                            brute_cont[idx, 1] = j
                            brute_cont[idx, 2] = num
                            idx += 1
            return idx

        # Bruteforce the filtered contingencies
        k = 0
        brute_cont = np.zeros((len(f)**2,3))
        c2 = np.zeros([count, count])
        print(f"Bruteforce enumeration over {int(np.sum(A0.ravel()) / 2)} pairs")
        for i in trange(count - 1):
            if np.sum(A0[i, :] > 0):
                k = compute_violation_numba(lodf, f, c2, lim, i, count, A0, brute_cont, k)
        print(f"Processed {100}% percent. Number of contingencies {k}; fake {np.sum(c2.flatten()) / 2}")
        if k:
            return False, brute_cont
        else:
            return True, None

    def ctg_autoinsert(self, object_type: str, options: Union[None, dict]=None):
        """Auto insert contingencies.

        :param object_type: Object type, e.g. branch.
        :param options: Optional. Pass a custom dictionary if you need
            to modify the Ctg_AutoInsert_Options.

        :returns: List of contingencies.
        """
        self.pw_order = True
        option = self.GetParametersMultipleElement('CTG_AutoInsert_Options_Value', ['Option', 'Value'])
        if object_type.lower() == 'branch':
            _object_type = 'LINE'
        elif object_type.lower() == 'bus':
            _object_type = 'BUS'
        elif object_type.lower() == 'load':
            _object_type = 'LOAD'
        elif object_type.lower() == 'transformer':
            _object_type = 'TRANSFORMER'
        mask = option['Option'] == 'ElementType'
        option.loc[mask, 'Value'] = _object_type
        if options:
            for key, value in options.items():
                _mask = option['Option'] == key
                option.loc[_mask, 'Value'] = value
        self.change_parameters_multiple_element_df('CTG_AutoInsert_Options_Value', option)
        self.RunScriptCommand("CTGAutoInsert;")
        return self.GetParametersMultipleElement('Contingency', ['Name', 'Skip'])

    def ctg_solveall(self):
        """
        Solve all of the contingencies that are not marked to be skipped.

        :returns: List of results.
        """
        self.pw_order = True
        self.RunScriptCommand("CTGSolveALL(NO,YES)")
        return self.GetParametersMultipleElement('Contingency', ['Name', 'Solved', 'Violations'])

    def _set_simauto_property(self, property_name, property_value):
        """Helper to just set a property name and value. Primary purpose
        of breaking things out this way is for testing.

        :param property_name: Name of the property to set, e.g.
            UIVisible.
        :param property_value: Value to set the property to, e.g. False.
        """
        setattr(self._pwcom, property_name, property_value)

    def update_ui(self) -> None:
        """Re-render the PowerWorld user interface (UI).

        :returns: None
        """
        return self.ProcessAuxFile(self.empty_aux)

    ####################################################################
    # SimAuto Server Functions
    ####################################################################

    def ChangeParameters(self, ObjectType: str, ParamList: list,
                         Values: list) -> None:
        """
        The ChangeParameters function has been replaced by the
        ChangeParametersSingleElement function. ChangeParameters
        can still be called as before, but will now just automatically
        call ChangeParametersSingleElement, and pass on the parameters
        to that function.
        Unlike the script SetData and CreateData commands, SimAuto does
        not have any explicit functions to create elements. Instead this
        can be done using the ChangeParameters functions by making use
        of the CreateIfNotFound SimAuto property. Set CreateIfNotFound =
        True if objects that are updated through the ChangeParameters
        functions should be created if they do not already exist in the
        case. Objects that already exist will be updated. Set
        CreateIfNotFound = False to not create new objects and only
        update existing ones. The CreateIfNotFound property is global,
        once it is set to True this applies to all future
        ChangeParameters calls.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/CloseCase_Function.htm>`__

        :param ObjectType: The type of object you are changing
            parameters for.
        :param ParamList: List of object field variable names. Note this
            MUST include the key fields for the given ObjectType
            (which you can get via the get_key_fields_for_object_type
            method).
        :param Values: List of values corresponding to the parameters in
            the ParamList.
        """
        return self.ChangeParametersSingleElement(ObjectType, ParamList,
                                                  Values)

    def ChangeParametersSingleElement(self, ObjectType: str, ParamList: list,
                                      Values: list) -> None:
        """Set a list of parameters for a single object.

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/ChangeParametersSingleElement_Function.htm>`__

        :param ObjectType: The type of object you are changing
            parameters for.
        :param ParamList: List of object field variable names. Note this
            MUST include the key fields for the given ObjectType
            (which you can get via the get_key_fields_for_object_type
            method).
        :param Values: List of values corresponding to the parameters in
            the ParamList.
        """
        return self._call_simauto('ChangeParametersSingleElement',
                                  ObjectType,
                                  convert_list_to_variant(ParamList),
                                  convert_list_to_variant(Values))

    def ChangeParametersMultipleElement(self, ObjectType: str, ParamList: list,
                                        ValueList: list) -> None:
        """Set parameters for multiple objects of the same type.

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/ChangeParametersMultipleElement_Function.htm>`__

        :param ObjectType: The type of object you are changing
            parameters for.
        :param ParamList: Listing of object field variable names. Note
            this MUST include the key fields for the given ObjectType
            (which you can get via the get_key_fields_for_object_type
            method).
        :param ValueList: List of lists corresponding to the ParamList.
            Should have length n, where n is the number of elements you
            with to change parameters for. Each sub-list should have
            the same length as ParamList, and the items in the sub-list
            should correspond 1:1 with ParamList.
        :returns: Result from calling SimAuto, which should always
            simply be None.

        :raises PowerWorldError: if PowerWorld reports an error.
        """
        # Call SimAuto and return the result (should just be None)
        return self._call_simauto('ChangeParametersMultipleElement',
                                  ObjectType,
                                  convert_list_to_variant(ParamList),
                                  convert_nested_list_to_variant(ValueList))

    def ChangeParametersMultipleElementFlatInput(self, ObjectType: str,
                                                 ParamList: list,
                                                 NoOfObjects: int,
                                                 ValueList: list) -> None:
        """
        The ChangeParametersMultipleElementFlatInput function allows
        you to set parameters for multiple objects of the same type in
        a case loaded into the Simulator Automation Server. This
        function is very similar to the ChangeParametersMultipleElement,
        but uses a single dimensioned array of values as input instead
        of a multi-dimensioned array of arrays.

        It is recommended that you use helper functions like
        ``change_parameters_multiple_element_df`` instead of this one,
        as it's simply easier to use.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/CloseCase_Function.htm>`__

        :param ObjectType: The type of object you are changing
            parameters for.
        :param ParamList: Listing of object field variable names. Note
            this MUST include the key fields for the given ObjectType
            (which you can get via the get_key_fields_for_object_type
            method).
        :param NoOfObjects: An integer number of devices that are
            passing values for. SimAuto will automatically check that
            the number of parameters for each device (counted from
            ParamList) and the number of objects integer correspond to
            the number of values in value list (counted from ValueList.)
        :param ValueList: List of lists corresponding to the ParamList.
            Should have length n, where n is the number of elements you
            with to change parameters for. Each sub-list should have
            the same length as ParamList, and the items in the sub-list
            should correspond 1:1 with ParamList.
        :return: Result from calling SimAuto, which should always
            simply be None.
        """
        # Call SimAuto and return the result (should just be None)
        if isinstance(ValueList[0], list):
            raise Error("The value list has to be a 1-D array")
        return self._call_simauto('ChangeParametersMultipleElementFlatInput',
                                  ObjectType,
                                  convert_list_to_variant(ParamList),
                                  NoOfObjects,
                                  convert_list_to_variant(ValueList))

    def CloseCase(self):
        """Closes case without saving changes.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/CloseCase_Function.htm>`__
        """
        return self._call_simauto('CloseCase')

    def GetCaseHeader(self, filename: str = None) -> Tuple[str]:
        """
        The GetCaseHeader function is used to extract the case header
        information from the file specified. A tuple of strings
        containing the contents of the case header or description is
        returned.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/GetCaseHeader_Function.htm>`__

        :param filename: The name of the file you wish to extract the
            header information from.
        :return: A tuple of strings containing the contents of the case
            header or description.
        """
        if filename is None:
            filename = self.pwb_file_path
        return self._call_simauto('GetCaseHeader', filename)

    def GetFieldList(self, ObjectType: str, copy=False) -> pd.DataFrame:
        """Get all fields associated with a given ObjectType.

        :param ObjectType: The type of object for which the fields are
            requested.
        :param copy: Whether or not to return a copy of the DataFrame.
            You may want a copy if you plan to make any modifications.

        :returns: Pandas DataFrame with columns from either
            SAW.FIELD_LIST_COLUMNS or SAW.FIELD_LIST_COLUMNS_OLD,
            depending on the version of PowerWorld Simulator being used.

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/GetFieldList_Function.htm>`__
        """
        # Get the ObjectType in lower case.
        object_type = ObjectType.lower()

        # Either look up stored DataFrame, or call SimAuto.
        try:
            output = self._object_fields[object_type]
        except KeyError:
            # We haven't looked up fields for this object yet.
            # Call SimAuto.
            result = self._call_simauto('GetFieldList', ObjectType)

            # Place result in a numpy array.
            result_arr = np.array(result)

            # Attempt to map results into a DataFrame using
            # FIELD_LIST_COLUMNS. If that fails, use
            # FIELD_LIST_COLUMNS_OLD.
            try:
                output = pd.DataFrame(result_arr,
                                      columns=self.FIELD_LIST_COLUMNS)
            except ValueError as e:
                # We may be dealing with the older convention.
                # The value error should read something like:
                # "Shape of passed values is (259, 4), indices imply (259, 5)"
                # Confirm via regular expressions.
                exp_base = r'\([0-9]+,\s'
                exp_end = r'{}\)'
                # Get number of columns for new/old lists.
                nf_old = len(self.FIELD_LIST_COLUMNS_OLD)
                nf_default = len(self.FIELD_LIST_COLUMNS)
                nf_new = len(self.FIELD_LIST_COLUMNS_NEW)
                # Search the error's arguments.
                r1 = re.search(exp_base + exp_end.format(nf_old), e.args[0])
                r2 = re.search(exp_base + exp_end.format(nf_default), e.args[0])
                r3 = re.search(exp_base + exp_end.format(nf_new), e.args[0])

                # Both results should match, i.e., not be None.
                if (r1 is None) or (r2 is None):
                    if r3 is None:
                        raise e
                    else:
                        # If we made it here, use the latest columns.
                        output = pd.DataFrame(result_arr,
                                              columns=self.FIELD_LIST_COLUMNS_NEW)
                else:
                    # If we made it here, use the older columns.
                    output = pd.DataFrame(result_arr,
                                          columns=self.FIELD_LIST_COLUMNS_OLD)

            # While it appears PowerWorld gives us the list sorted by
            # internal_field_name, let's make sure it's always sorted.
            output.sort_values(by=['internal_field_name'], inplace=True)

            # Store this for later.
            self._object_fields[object_type] = output

        # Either return a copy or not.
        return output.copy(deep=True) if copy else output

    def GetParametersSingleElement(self, ObjectType: str,
                                   ParamList: list, Values: list) -> pd.Series:
        """Request values of specified fields for a particular object.

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/GetParametersSingleElement_Function.htm>`__

        :param ObjectType: The type of object you're retrieving
            parameters for.
        :param ParamList: List of strings indicating parameters to
            retrieve. Note the key fields MUST be present. One can
            obtain key fields for an object type via the
            get_key_fields_for_object_type method.
        :param Values: List of values corresponding 1:1 to parameters in
            the ParamList. Values must be included for the key fields,
            and the remaining values should be set to 0.

        :returns: Pandas Series indexed by the given ParamList. This
            Series will be cleaned by clean_df_or_series, so data will
            be of the appropriate type and strings are cleaned up.

        :raises PowerWorldError: if the object cannot be found.
        :raises ValueError: if any given element in ParamList is not
            valid for the given ObjectType.
        :raises AssertionError: if the given ParamList and Values do
            not have the same length.
        """
        # Ensure list lengths match.
        assert len(ParamList) == len(Values), \
            'The given ParamList and Values must have the same length.'

        # Call PowerWorld.
        output = self._call_simauto('GetParametersSingleElement', ObjectType,
                                    convert_list_to_variant(ParamList),
                                    convert_list_to_variant(Values))

        # Convert to Series.
        s = pd.Series(output, index=ParamList)

        # Clean the Series and return.
        return self.clean_df_or_series(obj=s, ObjectType=ObjectType)

    def GetParametersMultipleElement(self, ObjectType: str, ParamList: list,
                                     FilterName: str = '') -> \
            Union[pd.DataFrame, None]:
        """Request values of specified fields for a set of objects in
        the load flow case.

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/GetParametersMultipleElement_Function.htm>`__

        :param ObjectType: Type of object to get parameters for.
        :param ParamList: List of variables to obtain for the given
            object type. E.g. ['BusNum', 'GenID', 'GenMW']. One
            can use the method GetFieldList to get a listing of all
            available fields. Additionally, you'll likely want to always
            return the key fields associated with the objects. These
            key fields can be obtained via the
            get_key_fields_for_object_type method.
        :param FilterName: Name of an advanced filter defined in the
            load flow case.

        :returns: Pandas DataFrame with columns matching the given
            ParamList. If the provided ObjectType is not present in the
            case, None will be returned.

        :raises PowerWorldError: if PowerWorld reports an error.
        :raises ValueError: if any parameters given in the ParamList
            are not valid for the given object type.

        TODO: Should we cast None to NaN to be consistent with how
            Pandas/Numpy handle bad/missing data?
        """
        output = self._call_simauto('GetParametersMultipleElement',
                                    ObjectType,
                                    convert_list_to_variant(ParamList),
                                    FilterName)
        if output is None:
            # Given object isn't present.
            return output

        # Create DataFrame.
        df = pd.DataFrame(np.array(output).transpose(),
                          columns=ParamList)

        # Clean DataFrame and return it.
        return self.clean_df_or_series(obj=df, ObjectType=ObjectType)

    def GetParametersMultipleElementFlatOutput(self, ObjectType: str,
                                               ParamList: list,
                                               FilterName: str = '') -> \
            Union[None, Tuple[str]]:
        """This function operates the same as the
        GetParametersMultipleElement function, only with one notable
        difference. The values returned as the output of the function
        are returned in a single-dimensional vector array, instead of
        the multi-dimensional array as described in the
        GetParametersMultipleElement topic.

        It is recommended that you use GetParametersMultipleElement
        instead, as you'll receive a DataFrame with correct data types.
        As this method is extraneous, the output from PowerWorld will
        be directly returned. This will show you just how useful ESA
        really is!

        :param ObjectType: Type of object to get parameters for.
        :param ParamList: List of variables to obtain for the given
            object type. E.g. ['BusNum', 'GenID', 'GenMW']. One
            can use the method GetFieldList to get a listing of all
            available fields. Additionally, you'll likely want to always
            return the key fields associated with the objects. These
            key fields can be obtained via the
            get_key_fields_for_object_type method.
        :param FilterName: Name of an advanced filter defined in the
            load flow case.

        :return:The format of the output array is the following: [
            NumberOfObjectsReturned, NumberOfFieldsPerObject,
            Ob1Fld1, Ob1Fld2, …, Ob(n)Fld(m-1), Ob(n)Fld(m)]
            The data is thus returned in a single dimension array, where
            the parameters NumberOfObjectsReturned and
            NumberOfFieldsPerObject tell you how the rest of the array
            is populated. Following the NumberOfObjectsReturned
            parameter is the start of the data. The data is listed as
            all fields for object 1, then all fields for object 2, and
            so on. You can parse the array using the NumberOf…
            parameters for objects and fields. If the given object
            type does not exist, the method will return None.
        """
        result = self._call_simauto(
            'GetParametersMultipleElementFlatOutput', ObjectType,
            convert_list_to_variant(ParamList),
            FilterName)

        if len(result) == 0:
            return None
        else:
            return result

    def GetParameters(self, ObjectType: str,
                      ParamList: list, Values: list) -> pd.Series:
        """This function is maintained in versions of Simulator later 
        than version 9 for compatibility with Simulator version 9. This 
        function will call the GetParametersSingleElement implicitly.
        
        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/GetParametersSingleElement_Function.htm>`__

        :param ObjectType: The type of object you're retrieving
            parameters for.
        :param ParamList: List of strings indicating parameters to
            retrieve. Note the key fields MUST be present. One can
            obtain key fields for an object type via the
            get_key_fields_for_object_type method.
        :param Values: List of values corresponding 1:1 to parameters in
            the ParamList. Values must be included for the key fields,
            and the remaining values should be set to 0.

        :returns: Pandas Series indexed by the given ParamList. This
            Series will be cleaned by clean_df_or_series, so data will
            be of the appropriate type and strings are cleaned up.

        :raises PowerWorldError: if the object cannot be found.
        :raises ValueError: if any given element in ParamList is not
            valid for the given ObjectType.
        :raises AssertionError: if the given ParamList and Values do
            not have the same length.
        """
        return self.GetParametersSingleElement(ObjectType, ParamList, Values)

    def GetSpecificFieldList(self, ObjectType: str, FieldList: List[str]) \
            -> pd.DataFrame:
        """
        The GetSpecificFieldList function is used to return identifying
        information about specific fields used by an object type. Note
        that in many cases simply using the GetFieldList method is
        simpler and gives more information.

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/GetSpecificFieldList_Function.htm>`__

        :param ObjectType: The type of object for which fields are
            requested.
        :param FieldList: A list of strings. Each string represents
            object field variables, as defined in the section on
            `PowerWorld Object Fields
            <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/PowerWorld_Object_Variables.htm>`__
            . Specific variablenames along with location numbers can be
            specified. To return all fields using the same variablename,
            use "variablename:ALL" instead of the location number that
            would normally appear after the colon. If all fields should
            be returned, a single parameter of "ALL" can be used instead
            of specific variablenames.

        :returns: A Pandas DataFrame with columns given by the class
            constant SPECIFIC_FIELD_LIST_COLUMNS. There will be a row
            for each element in the FieldList input unless 'ALL' is
            used in the FieldList. The DataFrame will be sorted
            alphabetically by the variablenames.
        """
        try:
            df = pd.DataFrame(
                self._call_simauto('GetSpecificFieldList', ObjectType,
                                   convert_list_to_variant(FieldList)),
                columns=self.SPECIFIC_FIELD_LIST_COLUMNS).sort_values(
                by=self.SPECIFIC_FIELD_LIST_COLUMNS[0]).reset_index(drop=True)
        except ValueError:
            df = pd.DataFrame(
                self._call_simauto('GetSpecificFieldList', ObjectType,
                                   convert_list_to_variant(FieldList)),
                columns=self.SPECIFIC_FIELD_LIST_COLUMNS_NEW).sort_values(
                by=self.SPECIFIC_FIELD_LIST_COLUMNS_NEW[0]).reset_index(drop=True)
        return df

    def GetSpecificFieldMaxNum(self, ObjectType: str, Field: str) -> int:
        """The GetSpecificFieldMaxNum function is used to return the
        maximum number of a fields that use a particular variablename
        for a specific object type.

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/GetSpecificFieldMaxNum_Function.htm>`__

        :param ObjectType: The type of object for which information is
            being requested.
        :param Field: The variablename for which the maximum number of
            fields is being requested. This should just be the
            variablename and should exclude the location number that can
            be included to indicate different fields that use the same
            variablename, i.e. do not include the colon and number that
            can be included when identifying a field.

        :returns: An integer that specifies the maximum number of fields
            that use the same variablename for a particular object type.
            Fields are identified in the format variablename:location
            when multiple fields use the same variablename. The output
            indicates the maximum number that the location can be.
            Generally, fields are identified starting from 0 and going
            up to the maximum number, but keep in mind that values
            within this range might be skipped and not used to indicate
            valid fields.
        """
        # Unfortunately, at the time of writing this method does not
        return self._call_simauto('GetSpecificFieldMaxNum', ObjectType, Field)

    def ListOfDevices(self, ObjType: str, FilterName='') -> \
            Union[None, pd.DataFrame]:
        """Request a list of objects and their key fields. This function
        is general, and you may be better off running more specific
        methods like "get_gens"

        :param ObjType: The type of object for which you are acquiring
            the list of devices. E.g. "Shunt," "Gen," "Bus," "Branch,"
            etc.
        :param FilterName: Name of an advanced filter defined in the
            load flow case open in the automation server. Use the
            empty string (default) if no filter is desired. If the
            given filter cannot be found, the server will default to
            returning all objects in the case of type ObjectType.

        :returns: None if there are no objects of the given type in the
            model. Otherwise, a DataFrame of key fields will be
            returned. There will be a row for each object of the given
            type, and columns for each key field. If the "BusNum"
            key field is present, the data will be sorted by BusNum.
        """
        # Start by getting the key fields associated with this object.
        kf = self.get_key_fields_for_object_type(ObjType)

        # Now, query for the list of devices.
        output = self._call_simauto('ListOfDevices', ObjType, FilterName)

        # If all data in the 2nd dimension comes back None, there
        # are no objects of this type and we should return None.
        all_none = True
        for i in output:
            if i is not None:
                all_none = False
                break

        if all_none:
            # TODO: May be worth adding logging here.
            return None

        # If we're here, we have this object type in the model.
        # Create a DataFrame.
        df = pd.DataFrame(output).transpose()
        # The return from get_key_fields_for_object_type is designed to
        # match up 1:1 with values here. Set columns.
        df.columns = kf['internal_field_name'].to_numpy()

        # Ensure the DataFrame has the correct types, is sorted by
        # BusNum, and has leading/trailing white space stripped.
        df = self.clean_df_or_series(obj=df, ObjectType=ObjType)

        # All done.
        return df

    def ListOfDevicesAsVariantStrings(self, ObjType: str, FilterName='') -> \
            tuple:
        """While this method is implemented, you are almost certainly
        better off using ListOfDevices instead. Since this method isn't
        particularly useful, no type casting will be performed on the
        output array. Contrast the results of calling this method with
        the results of calling ListOfDevices to see just how helpful
        ESA is!

        Description below if from
        `PowerWorld
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/ListOfDevicesAsVariantStrings_Function.htm>`__:

        This function operates the same as the ListOfDevices function,
        only with one notable difference. The values returned as the
        output of the function are returned as Variants of type String.
        The ListOfDevices function was errantly released returning the
        values strongly typed as Integers and Strings directly, whereas
        all other SimAuto functions returned data as Variants of type
        String. This function was added to also return the data in the
        same manner. This solved some compatibility issues with some
        software languages.

        :param ObjType: The type of object for which you are acquiring
            the list of devices.
        :param FilterName: The name of an advanced filter defined in the
            load flow case open in the Simulator Automation Server. If
            no filter is desired, then simply pass an empty string. If
            the filter cannot be found, the server will default to
            returning all objects in the case of type ObjType.

        :returns: Tuple of tuples as documented by PowerWorld for the
            ListOfDevices function.
        """
        return self._call_simauto('ListOfDevicesAsVariantStrings',
                                  ObjType, FilterName)

    def ListOfDevicesFlatOutput(self, ObjType: str, FilterName='') -> tuple:
        """While this method is implemented, you are almost certainly
        better off using ListOfDevices instead. Since this method isn't
        particularly useful, no type casting, data type changing, or
        data rearranging will be performed on the output array.
        Contrast the results of calling this method with the results of
        calling ListOfDevices to see just how helpful ESA is!

        This function operates the same as the ListOfDevices
        function, only with one notable difference. The values returned
        as the output of the function are returned in a
        single-dimensional vector array, instead of the
        multi-dimensional array as described in the ListOfDevices topic.
        The function returns the key field values for the device,
        typically in the order of bus number 1, bus number 2
        (where applicable), and circuit identifier (where applicable).
        These are the most common key fields, but some object types do
        have other key fields as well.

        `PowerWorld documentation:
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/ListOfDevicesFlatOutput_Function.htm>`__

        :param ObjType: The type of object for which you are acquiring
            the list of devices.
        :param FilterName: The name of an advanced filter defined in the
            load flow case open in the Simulator Automation Server. If
            no filter is desired, then simply pass an empty string. If
            the filter cannot be found, the server will default to
            returning all objects in the case of type ObjType.

        :returns: List in the following format:
            [NumberOfObjectsReturned, NumberOfFieldsPerObject, Ob1Fld1,
            Ob1Fld2, …, Ob(n)Fld(m-1), Ob(n)Fld(m)].
            The data is thus returned in a single dimension array, where
            the parameters NumberOfObjectsReturned and
            NumberOfFieldsPerObject tell you how the rest of the array
            is populated. Following the NumberOfObjectsReturned
            parameter is the start of the data. The data is listed as
            all fields for object 1, then all fields for object 2, and
            so on. You can parse the array using the NumberOf…
            parameters for objects and fields.
        """
        return self._call_simauto(
            'ListOfDevicesFlatOutput', ObjType, FilterName)

    def LoadState(self) -> None:
        """LoadState is used to load the system state previously saved
        with the SaveState function. Note that LoadState will not
        properly function if the system topology has changed due to the
        addition or removal of the system elements.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/LoadState_Function.htm>`__
        """
        return self._call_simauto('LoadState')

    def OpenCase(self, FileName: Union[str, None] = None) -> None:
        """Load PowerWorld case into the automation server.

        :param FileName: Full path to the case file to be loaded. If
            None, this method will attempt to use the last FileName
            used to open a case.

        :raises TypeError: if FileName is None, and OpenCase has never
            been called before.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/OpenCase_Function.htm>`__
        """
        # If not given a file name, ensure the pwb_file_path is valid.
        if FileName is None:
            if self.pwb_file_path is None:
                raise TypeError('When OpenCase is called for the first '
                                'time, a FileName is required.')
        else:
            # Set pwb_file_path according to the given FileName.
            self.pwb_file_path = FileName

        # Open the case. PowerWorld should return None.
        return self._call_simauto('OpenCase', self.pwb_file_path)

    def OpenCaseType(self, FileName: str, FileType: str,
                     Options: Union[list, str, None] = None) -> None:
        """
        The OpenCaseType function will load a PowerWorld Simulator load
         flow file into the Simulator Automation Server. This is similar
          to opening a file using the File > Open Case menu option in
          Simulator.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Default.htm#MainDocumentation_HTML/OpenCaseType_Function.htm?Highlight=OpenCaseType>`__

        :param FileName: Full path to the case file to be loaded. If
            None, this method will attempt to use the last FileName
            used to open a case.
        :param FileType: The type of case file to be loaded. It can be
            one of the following strings: PWB, PTI, PTI23, PTI24, PTI25,
            PTI26, PTI27, PTI28, PTI29, PTI30, PTI31, PTI32, PTI33,
            GE (means GE18), GE14, GE15, GE17, GE18, GE19, CF, AUX,
            UCTE, AREVAHDB
        :param Options: Optional parameter indicating special load
            options for PTI and GE file types. See the PowerWorld
            documentation for more details.
        """
        self.pwb_file_path = FileName
        if isinstance(Options, list):
            options = convert_list_to_variant(Options)
        elif isinstance(Options, str):
            options = Options
        else:
            options = ""
        return self._call_simauto('OpenCaseType', self.pwb_file_path,
                                  FileType, options)

    def ProcessAuxFile(self, FileName):
        """
        Load a PowerWorld Auxiliary file into SimAuto. This allows
        you to create a text file (conforming to the PowerWorld
        Auxiliary file format) that can list a set of data changes and
        other information for making batch changes in Simulator.

        :param FileName: Name of auxiliary file to load. Should be a
            full path.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/ProcessAuxFile_Function.htm>`__
        """
        return self._call_simauto('ProcessAuxFile', FileName)

    def RunScriptCommand(self, Statements):
        """Execute a list of script statements. The script actions are
        those included in the script sections of auxiliary files.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/RunScriptCommand_Function.htm>`__

        `Auxiliary File Format
        <https://github.com/mzy2240/ESA/blob/master/docs/Auxiliary%20File%20Format.pdf>`__
        """
        return self._call_simauto('RunScriptCommand', Statements)

    def SaveCase(self, FileName=None, FileType='PWB', Overwrite=True):
        """Save the current case to file.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/SaveCase_Function.htm>`__

        :param FileName: The name of the file you wish to save as,
            including file path. If None, the original path which was
            used to open the case (passed to this class's initializer)
            will be used.
        :param FileType: String indicating the format of the case file
            to write out. Here's what PowerWorld currently supports:
            * "PTI23": "PTI33" specific PTI version (raw).
            * "GE14": "GE21" GE PSLF version (epc).
            * "IEEE": IEEE common format (cf).
            * "UCTE": UCTE Data Exchange (uct).
            * "AUX": PowerWorld Auxiliary format (aux).
            * "AUXSECOND": PowerWorld Auxiliary format (aux) using
            secondary key fields.
            * "AUXLABEL": PowerWorld Auxiliary format (aux) using
            labels as key field identifiers.
            * "AUXNETWORK": PowerWorld Auxiliary format (aux) saving
            only network data.
            * "PWB5" through "PWB20": specific PowerWorld Binary
            version (pwb).
            * "PWB":  PowerWorld Binary (most recent) (pwb).
        :param Overwrite: Whether (True) or not (False) to overwrite the
            file if it already exists. If False and the specified file
            already exists, an exception will be raised.
        """
        if FileName is not None:
            f = convert_to_windows_path(FileName)
        elif self.pwb_file_path is None:
            raise TypeError('SaveCase was called without a FileName, but '
                            'it would appear OpenCase has not yet been '
                            'called.')
        else:
            f = convert_to_windows_path(self.pwb_file_path)

        return self._call_simauto('SaveCase', f, FileType, Overwrite)

    def SaveState(self) -> None:
        """SaveState is used to save the current state of the power
        system. This can be useful if you are interested in comparing
        various cases, much as the "Difference Flows" feature works in
        the Simulator application.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/SaveState_Function.htm>`__
        """
        return self._call_simauto('SaveState')

    def SendToExcel(self, ObjectType: str, FilterName: str, FieldList) -> None:
        """Send data from SimAuto to an Excel spreadsheet. While ESA
        provides this function, we strongly recommend you to use the
        ``GetParametersMultipleElement`` function and save the DataFrame
        directly to a .csv file using the DataFrame's ``to_csv``
        method. The problem with ``SendToExcel`` is that it opens
        (but does not save) an Excel sheet, which requires you to
        manually save it.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/SendToExcel_Function.htm>`__

        :param ObjectType: A String describing the type of object for
            which you are requesting data.
        :param FilterName: String with the name of an advanced filter
            which was previously defined in the case before being loaded
            in the Simulator Automation Server. If no filter is desired,
            then simply pass an empty string. If a filter name is passed
            but the filter cannot be found in the loaded case, no filter
            is used.
        :param FieldList: Variant parameter must either be an array of
            fields for the given object or the string "ALL". As an
            array, FieldList contains an array of strings, where each
            string represents an object field variable, as defined in
            the section on PowerWorld Object Variables. If, instead of
            an array of strings, the single string "ALL" is passed, the
            Simulator Automation Server will use predefined default
            fields when exporting the data.

        :returns: None
        """
        return self._call_simauto('SendToExcel', ObjectType, FilterName,
                                  FieldList)

    def TSGetContingencyResults(self, CtgName: str, ObjFieldList: List[str],
                                StartTime: Union[None, int, float] = None,
                                StopTime: Union[None, int, float] = None) -> \
            Union[Tuple[None, None], Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        WARNING: This function should only be used after the simulation
        is run (for example, use this after running script commands
        TSSolveAll or TSSolve).

        On to the main documentation:

        The TSGetContingencyResults function is used to read
        transient stability results into an external program (Python)
        using SimAuto.

        This function is analogous to the script command TSGetResults,
        where rather than saving out results to a file, the results are
        passed back directly to the SimAuto COM object and may be
        further processed by an external program. As with TSGetResults,
        this function should only be used after the simulation is run
        (for example, use this after running script commands TSSolveAll
        or TSSolve).

        `PowerWorld documentation:
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/TSGetContingencyResults%20Function.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Functions%7C_____49>`__

        The authors of ESA do not have extensive experience running
        transient contingencies in PowerWorld, so this method has not
        been tested as extensively as we would prefer. If your case/code
        has issues with this method, please file an issue on `GitHub
        <https://github.com/mzy2240/ESA/issues>`__.

        :param CtgName: The contingency to obtain results from. Only one
            contingency be obtained at a time.
        :param ObjFieldList: A list of strings which may contain plots,
            subplots, or individual object/field pairs specifying the
            result variables to obtain. For field name please check
            `here <https://mzy2240.github.io/ESA/html/overview.html#powerworld-variables>`__.

        :param StartTime: The time in seconds in the simulation to begin
            retrieving results. If not specified (None), the start time
            of the simulation is used.
        :param StopTime: The time in seconds in the simulation to stop
            retrieving results. If not specified, the end time of the
            simulation is used.

        :returns: A tuple containing two DataFrames, "meta" and "data."
            Alternatively, if the given CtgName does not exist, a tuple
            of (None, None) will be returned.
            The "meta" DataFrame describes the data in the "data"
            DataFrame, and can be used to map objects to columns in
            the "data" DataFrame. The "meta" DataFrame's columns are:
            ['ObjectType', 'PrimaryKey', 'SecondaryKey', 'Label',
            'VariableName', 'ColHeader']. Each row in the "meta"
            DataFrame corresponds to a column in the "data" DataFrame.
            So the "meta" row with index label 0 corresponds to the
            column labeled 0 in the "data" DataFrame, and so forth.
            Unfortunately, the ``ObjectType``s that come back from
            PowerWorld do not always match valid ``ObjectType``
            variable names (e.g. "Generator" comes back as an
            ``ObjectType``, but attempting to use "Generator" in the
            ``GetParametersMultipleElement`` method results in an
            error), so ESA's ability to perform automatic data type
            transformation is limited. All columns in the "data"
            DataFrame will be cast to numeric types by
            ``pandas.to_numeric``. If Pandas cannot determine an
            appropriate numeric type, the data will be unmodified (i.e.,
            the type will not be changed). In addition to the integer
            labeled columns which match the "meta" rows, the "data"
            DataFrame additionally has a "time" column which corresponds
            to the timestamp (in seconds).
        """
        out = self._call_simauto('TSGetContingencyResults', CtgName,
                                 ObjFieldList, str(StartTime), str(StopTime))

        # We get (None, (None,)) if the contingency does not exist.
        if out == (None, (None,)):
            return None, None

        # Length should always be 2.
        assert len(out) == 2, 'Unexpected return format from PowerWorld.'

        # Extract the meta data.
        meta = pd.DataFrame(
            out[0], columns=['ObjectType', 'PrimaryKey', 'SecondaryKey',
                             'Label', 'VariableName', 'ColHeader'])

        # Remove extraneous white space in the strings.
        # https://stackoverflow.com/a/40950485/11052174
        meta = meta.apply(lambda x: x.str.strip(), axis=0)

        # Extract the data.
        data = pd.DataFrame(out[1])

        # Decrement all the columns by 1 so that they line up with the
        # 'meta' frame.
        data.rename(columns=lambda x: x - 1, inplace=True)

        # Rename first column to 'time'.
        data.rename(columns={-1: 'time'}, inplace=True)

        # Attempt to convert all columns to numeric.
        data = self._to_numeric(data, errors='ignore')

        # Return.
        return meta, data

    def WriteAuxFile(self, FileName: str, FilterName: str, ObjectType: str,
                     FieldList: Union[list, str],
                     ToAppend=True):
        """The WriteAuxFile function can be used to write data from the
        case in the Simulator Automation Server to a PowerWorld
        Auxiliary file. The name of an advanced filter which was
        PREVIOUSLY DEFINED in the case before being loaded in the
        Simulator Automation Server. If no filter is desired, then
        simply pass an empty string. If a filter name is passed but the
        filter cannot be found in the loaded case, no filter is used.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/WriteAuxFile_Function.htm>`__


        """
        return self._call_simauto('WriteAuxFile', FileName,
                                  FilterName, ObjectType, ToAppend,
                                  FieldList)

    ####################################################################
    # PowerWorld ScriptCommand helper functions
    ####################################################################

    def SolvePowerFlow(self, SolMethod: str = 'RECTNEWT') -> None:
        """Run the SolvePowerFlow command.

        :param SolMethod: Solution method to be used for the Power Flow
            calculation. Case insensitive. Valid options are:
            'RECTNEWT' - Rectangular Newton-Raphson
            'POLARNEWTON' - Polar Newton-Raphson
            'GAUSSSEIDEL' - Gauss-Seidel
            'FASTDEC' - Fast Decoupled
            'ROBUST' - Attempt robust solution process
            'DC' - DC power flow

        See
        `Auxiliary File Format.pdf
        <https://github.com/mzy2240/ESA/blob/master/docs/Auxiliary%20File%20Format.pdf>`__
        for more details.
        """
        script_command = f"SolvePowerFlow({SolMethod.upper()})"
        return self.RunScriptCommand(script_command)

    def OpenOneLine(self, filename: str, view: str = "",
                    FullScreen: str = "NO", ShowFull: str = "NO",
                    LinkMethod: str = "LABELS", Left: float = 0.0,
                    Top: float = 0.0, Width: float = 0.0, Height: float = 0.0) \
            -> None:
        """Use this function to open a oneline diagram. This function
        can be used to associate onelines with a PWB file.

        :param filename: The file name of the oneline diagram to open.
        :param view: The view name that should be opened. Pass an empty
            string to denote no specific view.
        :param FullScreen: Set to YES or NO. YES means that the oneline
            diagram will be open in full screen mode. If this parameter
            is not specified, then NO is assumed.
        :param ShowFull: Optional parameter. Set to YES to open the
            oneline and apply the Show Full option. Set to NO to open
            the oneline and leave the oneline as is. Default is NO if
            not specified.
        :param LinkMethod: Optional Parameter that controls oneline
            linking. LABELS, NAMENOMKV, and NUMBER will link using the
            respective key fields.
        :param Left: Optional with default of 0. Value between 0 and 100
            that indicates the location of the left edge of the oneline
            as a percentage of the Simulator/Retriever window width.
        :param Top: Optional with default of 0. Value between 0 and 100
            that indicates the top edge of the oneline as a percentage
            of the Simulator/Retriever window height.
        :param Width: Optional with default of 0. Value between 0 and
            100 that indicates the width of the oneline as a percentage
            of the Simulator/Retriever window width.
        :param Height: Optional with default of 0. Value between 0 and
            100 that indicates the height of the oneline as a percentage
            of the Simulator/Retriever window height.

        :returns: None
        """
        script = 'OpenOneline("{}", {}, {} {})'.format(
            filename, view, FullScreen, ShowFull, LinkMethod, Left, Top,
            Width, Height)
        return self.RunScriptCommand(script)

    def CloseOneline(self, OnelineName: str = "") -> None:
        """Use this action to close an open oneline diagram without
         saving it. If the name is omitted, the last focused oneline 
         diagram will be closed.

         :param OnelineName: The name of the oneline diagram to close.

         :returns: None
         """
        script = f'CloseOneline({OnelineName})'
        return self.RunScriptCommand(script)

    ####################################################################
    # PowerWorld SimAuto Properties
    ####################################################################
    @property
    def CreateIfNotFound(self):
        """The CreateIfNotFound property of the Simulator Automation
        Server is useful when you are changing data with the
        ChangeParameters functions. Set the attribute through the
        ``set_simauto_property`` method.
        """
        return self._pwcom.CreateIfNotFound

    @property
    def CurrentDir(self) -> str:
        """The CurrentDir property of the Simulator Automation Server
        allows you to retrieve or set the working directory for the
        currently running SimulatorAuto process. This is most useful if
        using relative filenames (e.g. ``"relativename.aux"`` versus
        ``r"C:\Program Files\PowerWorld\Working\abosultename.aux"``)
        when specifying files. Set this property through the
        ``set_simauto_property`` method.
        """
        return self._pwcom.CurrentDir

    @property
    def ProcessID(self) -> int:
        """The ProcessID property of the Simulator Automation Server
        allows you to retrieve the process ID of the currently running
        SimulatorAuto process, as can also be seen through the Task
        Manager in Windows. This information can be useful if a forced
        shutdown of the SimulatorAuto object is needed, as all calls to
        the SimulatorAuto object are synchronous. This means the
        SimulatorAuto object will not be destroyed until all calls, no
        matter the time of execution, have completed.
        """
        return self._pwcom.ProcessID

    @property
    def RequestBuildDate(self) -> int:
        """The RequestBuildDate property of the Simulator Automation
        Server allows you to retrieve the build date of the PowerWorld
        Simulator executable currently running with the SimulatorAuto
        process. The property returns an integer value that represents a
        date. This information is useful for verifying the release
        version of the executable.

        After contacting PowerWorld, it seems the integer comes back
        according to Delphi date conventions, which counts days since
        December 30th, 1899.
        """
        return self._pwcom.RequestBuildDate

    @property
    def UIVisible(self) -> bool:
        """Get the UIVisible property of the Simulator Automation
        Server which indicates the visibility of the user interface for
        Simulator. Default behavior is to not show the user interface
        while using SimAuto. Set this property through the
        ``set_simauto_property`` method.
        """
        try:
            return self._pwcom.UIVisible
        except AttributeError:
            self.log.warning(
                'UIVisible attribute could not be accessed. Note this SimAuto '
                'property was not introduced until Simulator version 20. '
                'Check your version with the get_simulator_version method.')
            return False

    ####################################################################
    # Private Methods
    ####################################################################

    def _call_simauto(self, func: str, *args):
        """Helper function for calling the SimAuto server.

        :param func: Name of PowerWorld SimAuto function to call.

        :param args: Remaining arguments to this function will be
            passed directly to func.

        :returns: Result from PowerWorld. This will vary from function
            to function. If PowerWorld returns ('',), this method
            returns None.

        :raises PowerWorldError: If PowerWorld indicates an exception
            occurred.

        :raises AttributeError: If the given func is invalid.

        :raises COMError: If attempting to call the SimAuto function
            results in an error.

        The listing of valid functions can be found in PowerWorld's
        `web help
        <https://www.powerworld.com/WebHelp/>`__.
        """
        # Get a reference to the SimAuto function from the COM object.
        try:
            f = getattr(self._pwcom, func)
        except AttributeError:
            raise AttributeError(f'The given function, {func}, is not a valid SimAuto function.') from None


        # Call the function.
        try:
            output = f(*args)
        except Exception as e:
            m = f'An error occurred when trying to call {func} with {args}'
            self.log.exception(m)
            raise COMError(m) from e

        # handle errors
        if output == ('',):
            # If we just get a tuple with the empty string in it,
            # there's nothing to return.
            return None

        # There's one inconsistent method, GetFieldMaxNum, which
        # appears to return -1 on error, otherwise simply an integer.
        # Since that's an edge case, we'll use a try/except block.
        try:
            if output is None or output[0] == '':
                pass
            elif 'No data' not in output[0]:
                raise PowerWorldError(output[0])

        except TypeError as e:
            # We'll get 'is not subscriptable' if PowerWorld simply
            # returned an integer, as will happen with GetFieldMaxNum.
            if 'is not subscriptable' in e.args[0]:
                if output == -1:
                    # Apparently -1 is the signal for an error.
                    m = (
                        'PowerWorld simply returned -1 after calling '
                        "'{func}' with '{args}'. Unfortunately, that's all "
                        "we can help you with. Perhaps the arguments are "
                        "invalid or in the wrong order - double-check the "
                        "documentation.").format(func=func, args=args)
                    raise PowerWorldError(m) from e
                elif isinstance(output, int):
                    # Return the integer.
                    return output

            # If we made it here, simply re-raise the exception.
            raise e

        # After errors have been handled, return the data. Typically
        # this is in position 1.
        return output[1] if len(output) == 2 else output[1:]

    def _change_parameters_multiple_element_df(
            self, ObjectType: str, command_df: pd.DataFrame) -> pd.DataFrame:
        """Private helper for changing parameters for multiple elements
        with a command DataFrame as input. See docstring for public
        method "change_parameters_multiple_element_df" for more details.

        :returns: "Cleaned" version of command_df (passed through
            clean_df_or_series).
        """
        # Start by cleaning up the DataFrame. This will avoid silly
        # issues later (e.g. comparing ' 1 ' and '1').
        cleaned_df = self.clean_df_or_series(obj=command_df,
                                             ObjectType=ObjectType)

        # Convert columns and data to lists and call PowerWorld.
        # noinspection PyTypeChecker
        self.ChangeParametersMultipleElement(
            ObjectType=ObjectType, ParamList=cleaned_df.columns.tolist(),
            ValueList=cleaned_df.to_numpy().tolist())

        return cleaned_df

    def _df_equiv_subset_of_other(self, df1: pd.DataFrame, df2: pd.DataFrame,
                                  ObjectType: str) -> bool:
        """Helper to indicate if one DataFrame is an equivalent subset
        of another (True) or not (False) for a given PowerWorld object
        type. Here, we're defining "equivalent subset" as all of df1
        being present in df2 (e.g. columns, index, values, etc.), and
        all data are "equivalent." Numeric data will be compared with
        Numpy's "allclose" function, and string data will be compared
        with Numpy's "array_equal" function. Types will be cast based on
        the given parameters (columns in the DataFrame).

        :param df1: First DataFrame. Could possibly originate from a
            method such as "GetParametersMultipleElement." Column names
            should be PowerWorld variable names, and the key fields
            should be included.
        :param df2: Second DataFrame. See description of df1.
        :param ObjectType: PowerWorld object type for which the
            DataFrames represent data for. E.g. 'gen' or 'load'.

        :returns: True if DataFrames are "equivalent," False otherwise.
        """
        # Get the key fields for this ObjectType.
        kf = self.get_key_fields_for_object_type(ObjectType=ObjectType)

        # Merge the DataFrames on the key fields.
        merged = pd.merge(left=df1, right=df2, how='inner',
                          on=kf['internal_field_name'].tolist(),
                          suffixes=('_in', '_out'), copy=False)

        # Time to check if our input and output values match. Note this
        # relies on our use of "_in" and "_out" suffixes above.
        cols_in = merged.columns[merged.columns.str.endswith('_in')]
        cols_out = merged.columns[merged.columns.str.endswith('_out')]

        # We'll be comparing string and numeric columns separately. The
        # numeric columns must use np.allclose to avoid rounding error,
        # while the strings should use array_equal as the strings should
        # exactly match.
        cols = cols_in.str.replace('_in', '')
        numeric_cols = self.identify_numeric_fields(ObjectType=ObjectType,
                                                    fields=cols)
        str_cols = ~numeric_cols

        # If all numeric data are "close" and all string data match
        # exactly, this will return True. Otherwise, False will be
        # returned.
        return (
                np.allclose(
                    merged[cols_in[numeric_cols]].to_numpy(),
                    merged[cols_out[numeric_cols]].to_numpy()
                )
                and
                np.array_equal(
                    merged[cols_in[str_cols]].to_numpy(),
                    merged[cols_out[str_cols]].to_numpy()
                )
        )

    def _to_numeric(self, data: Union[pd.DataFrame, pd.Series],
                    errors='raise') -> \
            Union[pd.DataFrame, pd.Series]:
        """Helper to convert data from string to numeric. The primary
        purpose for this function's existence is to handle European style
        decimal separators (comma vs. period).

        :param data: DataFrame or Series which will be have its data
            converted to numeric types.
        :param errors: Passed directly to pandas.to_numeric, please
            consult the Pandas documentation. Available options at the
            time of writing are 'ignore', 'raise', and 'coerce'
        :returns: data, but with all columns converted to numeric. Note
            that if the errors parameter is 'ignore' that it's possible
            not all data will be converted to numeric due to suppressed
            errors. Also note that data which is already numeric will
            remain unaltered.
        """
        # Determine if we're dealing with a DataFrame or Series.
        if isinstance(data, pd.DataFrame):
            df_flag = True
        elif isinstance(data, pd.Series):
            df_flag = False
        else:
            raise TypeError('data must be either a DataFrame or Series.')

        # to_numeric from Pandas does not at the time of writing
        # (2020-06-12) have a decimal delimiter argument, while to_csv
        # and from_csv do. So, we have to check.
        if self.decimal_delimiter != '.':
            # Replace commas with periods.

            if df_flag:
                # Need to use apply to strip strings from multiple columns.
                data = data.apply(self._replace_decimal_delimiter)

            else:
                # A series is much simpler, and the .str.replace()
                # method can be used directly.
                data = self._replace_decimal_delimiter(data)

        # Convert to numeric and return.
        if df_flag:
            return data.apply(lambda x: pd.to_numeric(x, errors=errors))
        else:
            return data.apply(pd.to_numeric, errors=errors)

    def _replace_decimal_delimiter(self, data: pd.Series):
        """Helper to replace the decimal delimiter character with a
        period. IMPORTANT NOTE: If the given Series does not have the
        'str' attribute, this method assumes the data is already
        numeric. the associated AttributeError will be ignored.

        :param data: Pandas Series to replace self.decimal_delimiter
            with a '.' character.
        :returns: data, but with string replacement. If data does not
            have the 'str' attribute, data is returned unmodified.
        """
        try:
            return data.str.replace(self.decimal_delimiter, '.')
        except AttributeError:
            return data


def df_to_aux(fp, df, object_name: str):
    """ Convert a dataframe to PW aux/axd data section.

    :param fp: file handler
    :param df: dataframe
    :param object_name: object type
    """
    # write the header
    fields = ','.join(df.columns.tolist())
    header = f"DATA ({object_name}, [{fields}])"
    header_chunks = header.split(',')
    i = 0
    line_width = 0
    max_width = 86
    working_line = []
    container = []
    while True:
        if line_width + len(header_chunks[i]) <= max_width:
            working_line.append(header_chunks[i])
            line_width += len(header_chunks[i])
            i += 1
        else:
            container.append(','.join(working_line))
            working_line = []
            line_width = 0
        if i == len(header_chunks):
            if len(working_line):
                container.append(','.join(working_line))
            break
    container = [ls + "," for ls in container[:-1]] + [container[-1]]
    container = [container[0]] + ["    " + ls for ls in container[1:]]  # add tab to each line

    # write the remaining part
    container.append("{")
    container.extend(json.dumps(row, separators=(' ', ': '))[1:-1] for row in df.values.tolist())
    container.append("}\r\n")
    fp.write('\n'.join(container))


def convert_to_windows_path(p):
    """Given a path, p, convert it to a Windows path."""
    return str(PureWindowsPath(p))


def convert_list_to_variant(list_in: list) -> VARIANT:
    """Given a list, convert to a variant array.

    :param list_in: Simple one-dimensional Python list, e.g. [1, 'a', 7]
    """
    # noinspection PyUnresolvedReferences
    return VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY, list_in)


def convert_nested_list_to_variant(list_in: list) -> List[VARIANT]:
    """Given a list of lists, convert to a variant array.

    :param list_in: List of lists, e.g. [[1, '1'], [1, '2'], [2, '1']]
    """
    return [convert_list_to_variant(sub_array) for sub_array in list_in]


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class PowerWorldError(Error):
    """Raised when PowerWorld reports an error following a SimAuto call.
    """
    pass


class COMError(Error):
    """Raised when attempting to call a SimAuto function results in an
    error.
    """
    pass


class CommandNotRespectedError(Error):
    """Raised if a command sent into PowerWorld is not respected, but
    PowerWorld itself does not raise an error. This exception should
    be used with helpers that double-check commands.
    """
    pass
