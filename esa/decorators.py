from .exceptions import FileException, GeneralException, ConvergenceException


def handle_file_exception(func):
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        if self.__pwerr__():
            raise FileException(self.error_message)
        return True
    return wrapper


def handle_general_exception(func):
    def wrapper(self, *args, **kwargs):
        output = func(self, *args, **kwargs)
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        elif self.error_message != '':
            raise GeneralException(self.error_message)
        else:
            return output
    return wrapper


def handle_convergence_exception(func):
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        if self.__pwerr__():
            raise ConvergenceException(self.error_message)
        return True
    return wrapper
