'''Contains the shared definition of the init_dir_path'''

import os
import os.path

def init_dir_path(path):
    ''' Returns an existing absolute directory with files stripped
        if necessary.

        Args:
            path: A string directory path. File paths will have the
                  file removed and the base directory returned.

        Returns:
            A directory path string.
    '''
    # Expand home directory '~'
    path = os.path.expanduser(path)

    # Expand current/up directory './..'
    path = os.path.abspath(path)

    # Were we given a file or directory name?
    base, ext = os.path.splitext(path)
    if ext:  #Yup we got a file when expecting a directory
        # Let's not fail just yet.  Strip the file and use the
        # base directory as our path
        path = os.path.dirname(path)

    if not os.path.exists(path):
        os.mkdir(path)

    return path

