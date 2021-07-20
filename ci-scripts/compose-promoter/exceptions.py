"""
Compose promoter exception classes.
"""


class ComposePromoterNotSupported(Exception):
    """Error caught while communicating with a remote server."""

    def __init__(self, details):
        error_msg = ("Compose promotion not supported. Details: %s" % details)
        super(ComposePromoterNotSupported, self).__init__(error_msg)


class ComposePromoterServerConnError(Exception):
    """Error caught while communicating with a remote server."""

    def __init__(self, details):
        error_msg = ("Caught an error while communicating with remote server. " 
                     "Details: %s" % details)
        super(ComposePromoterServerConnError, self).__init__(error_msg)


class ComposePromoterOperationError(Exception):
    """Error caught while sending commands to a remote server."""

    def __init__(self, operation, details=None):
        error_msg = ("Failed to execute '%(operation)s' operation in remote "
                     "server. %(details)s" % {
                         'operation': operation,
                         'details': details or '',
                     })
        super(ComposePromoterOperationError, self).__init__(error_msg)
