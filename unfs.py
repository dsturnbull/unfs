#!/usr/bin/env python
"""
unfs.py mounts the UNFS filesystem to mountpoint and daemonizes.
"""

# ignore complaint about '*args **kwargs' magic.. :P
# pylint: disable-msg=W0142

import os, errno, random, fuse, time, logging, statvfs
from fuse import Fuse

# config
try:
    base = os.path.split(os.sys.argv[1])[0]
    os.path.exists(base)

    if base == '/':
        base = ''

    mountPoint = base + '/unfs'
    nodeMountPoint = base + '/fs'
except IndexError:
    base = '/'
    mountPoint = '/unfs'
    nodeMountPoint = '/fs'

fuse.fuse_python_api = (0, 2)
logLevel = logging.CRITICAL
unfsNodes = []
unfsNodeLastUpdate = 0

logging.basicConfig(level=logLevel, 
    format='%(asctime)s %(levelname)s %(message)s',
    filename='/tmp/unfs.log',
)

def flag2mode(flags):
    """
    Rewrite flags to mode list
    """

    md = {
        os.O_RDONLY:'r',
        os.O_WRONLY:'w',
        os.O_RDWR:'w+'
    }
    m = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

    if flags | os.O_APPEND:
        m = m.replace('w', 'a', 1)

    return m

def findNewNodes():
    """
    Loop through nodeMountPoint to find all nodes mounted.
    """

    # ignore global warning for clarity
    # pylint: disable-msg=W0603
    global unfsNodes, unfsNodeLastUpdate
    now = time.time()

    if now - unfsNodeLastUpdate > 10:
        logging.critical('finding nodes in %s' % nodeMountPoint)
        unfsNodes = []
        nodes = []
        for node in os.listdir(nodeMountPoint):
            nodes.append(nodeMountPoint + '/' + node)

        unfsNodes = nodes
        logging.info(unfsNodes)
        unfsNodeLastUpdate = now
    logging.critical(unfsNodes)

def unfsRandom():
    """
    Picks the best (not random) node to write to.
    """

    best = 0
    bestNode = None
    nodeSizes = {}

    for node in unfsNodes:
        st = os.statvfs(node)
        freeSpace = st[statvfs.F_BAVAIL]*st[statvfs.F_BSIZE]
        nodeSizes[freeSpace] = 1
        if freeSpace > best:
            bestNode = node
            best = freeSpace

    # if all are equal, force a random choice
    if bestNode and len(nodeSizes.keys()) > 1:
        node = bestNode
        logging.debug('best node: %s' % node)
    else:
        node = unfsNodes[random.randrange(len(unfsNodes))]
        logging.debug('random node: %s' % node)

    # FIXME: locking
    return node

class UNFS(Fuse):
    """
    Main UNFS class.
    """

    def __init__(self, *args, **kw):
        """
        Init main UNFS class.
        """

        self.file_class = None
        Fuse.__init__(self, *args, **kw)

    def getattr(self, path):
        """
        os.lstat wrapper. lstat because we don't want to make symlinks
        appear to be actual files.
        """

        logging.debug('getattr %s' % path)
        for node in unfsNodes:
            newPath = node + path
            logging.debug('_getattr %s' % newPath)
            try:
                logging.debug(os.lstat(newPath))
                return os.lstat(newPath)
            except OSError, why:
                logging.debug('getattr %s failed: %s' % (newPath, why))

        return -errno.ENOENT

    def readlink(self, path):
        """
        os.readlink wrapper
        """

        logging.debug('readlink %s' % path)

        for node in unfsNodes:
            newPath = node + path
            try:
                return os.readlink(newPath)
            except OSError, why:
                logging.debug('readlink %s failed: %s' % (newPath, why))

    def readdir(self, path, offset):
        """
        Return files in dir, add in '.' and '..'.
        """

        # FIXME: should probably use generated '.' and '..' based on aggregates
        logging.debug('readdir %s %s' % (path, offset))
        contents = {}
        for node in unfsNodes:
            newPath = node + path
            try:
                for dirFile in os.listdir(newPath):
                    if dirFile != '':
                        contents[dirFile] = fuse.Direntry(dirFile)
            except OSError, why:
                logging.debug('readdir %s failed: %s' % (newPath, why))

        contents['.'] = fuse.Direntry('.')
        contents['..'] = fuse.Direntry('..')

        for dirFile, entry in contents.iteritems():
            yield entry

    def unlink(self, path):
        """
        Unlink file.
        """

        logging.debug('unlink %s' % path)
        for node in unfsNodes:
            newPath = node + path
            try:
                os.unlink(newPath)
                logging.critical('del file: %s' % newPath)
            except OSError, why:
                logging.debug('unlink %s failed: %s' % (newPath, why))

    def rmdir(self, path):
        """
        rmdir. Removes dir on all nodes.
        """

        # FIXME: this will succeed on some nodes that don't have files yet...
        
        logging.debug('rmdir %s' % path)
        for node in unfsNodes:
            newPath = node + path
            try:
                os.rmdir(newPath)
            except OSError, why:
                logging.debug('rmdir %s failed: %s' % (newPath, why))

    def symlink(self, path, path1):
        """
        Symlink.
        """

        newPath = unfsRandom() + path1
        logging.debug('symlink %s %s' % (path, newPath))
        os.symlink(path, newPath)

    def rename(self, path, path1):
        """
        Rename file, basically mv.
        Have to be careful to only rename files on the same filesystem.
        """

        logging.debug('mv %s %s' % (path, path1))
        newPath = unfsRandom() + path1
        for node in unfsNodes:
            # FIXME: moved files will end up on other nodes, which is slow.
            oldPath = node + path
            try:
                logging.debug('mv %s %s' % (oldPath, newPath))
                os.rename(oldPath, newPath)
            except OSError, why:
                logging.debug('mv %s %s failed: %s' % (oldPath, newPath, why))

    def link(self, path, path1):
        """
        hard link.
        """

        newPath = unfsRandom() + path1
        logging.debug('hard link %s -> %s (%s)' % (path, path1, newPath))
        os.link(path, newPath)

    def chmod(self, path, mode):
        """
        chmod.
        """

        logging.debug('chmod %s %s' % (path, mode))
        for node in unfsNodes:
            newPath = node + path
            try:
                os.chmod(newPath, mode)
            except OSError, why:
                logging.debug('chmod %s %s failed: %s' % (path, mode, why))

    def chown(self, path, user, group):
        """
        Change ownership of file.
        """

        logging.debug('chown %s %s:%s' % (path, user, group))
        for node in unfsNodes:
            newPath = node + path
            try:
                os.chown(newPath, user, group)
            except OSError, why:
                logging.debug('chown %s %s:%s failed: %s' % \
                    (path, user, group, why))

    def truncate(self, path, length):
        """
        Truncate file. Don't know why this isn't covered by UnfsFile.truncate.
        """

        logging.debug('truncate %s to %s'  % (path, length))
        for node in unfsNodes:
            newPath = node + path
            try:
                os.stat(newPath)
                f = open(newPath, "a")
                f.truncate(length)
                f.close()
            except OSError, why:
                logging.debug('truncate %s to %s failed: %s' % \
                    (path, length, why))

    def mknod(self, path, mode, dev):
        """
        Make node thingy.
        """

        logging.debug('mknod %s %s %s' % (path, mode, dev))
        newPath = unfsRandom() + path
        os.mknod(newPath, mode, dev)

    def mkdir(self, path, mode):
        """
        Make a directory.
        Makes it on each node, but it is not an error to not be able to on some
        nodes.
        """

        logging.debug('mkdir %s (%s)' % (path, mode))
        for node in unfsNodes:
            newPath = node + path
            try:
                logging.debug('mkdir %s' % newPath)
                os.mkdir(newPath, mode)
            except OSError, why:
                logging.debug('mkdir %s failed: %s' % (newPath, why))

    def utime(self, path, times):
        """
        Set access and modified time on file.
        If times is None, set to current time.
        """

        logging.debug('utime on %s to %s' % (path, times))
        for node in unfsNodes:
            newPath = node + path
            try:
                os.utime(newPath, times)
            except (OSError, TypeError), why:
                logging.debug('utime on %s to %s failed: %s' % \
                    (path, times, why))

    def access(self, path, mode):
        """
        Check for access on a file with specific mode.
        """

        logging.debug('access: %s %s' % (path, mode))
        yes = 0
        for node in unfsNodes:
            newPath = node + path
            yes |= os.access(newPath, mode)

        if not yes:
            return -errno.EACCES

    def statfs(self):
        """
        Returns info for use by 'df' etc.
        Basically we add up all the addable values from underlying node statfs
        calls, making sure to convert them into equal sized blocks.
        """

        logging.debug('statfs')
        my_bsize = 4096

        st = fuse.StatVfs()
        st.f_bsize = my_bsize
        st.f_frsize = my_bsize
        st.f_blocks = 0
        st.f_bfree = 0
        st.f_bavail = 0
        st.f_files = 0
        st.f_ffree = 0

        for node in unfsNodes:
            nst = os.statvfs(node)
            div = nst[statvfs.F_FRSIZE]/my_bsize
            st.f_blocks += nst[statvfs.F_BLOCKS] \
                * nst[statvfs.F_FRSIZE] / my_bsize
            st.f_bfree  += nst[statvfs.F_BFREE] \
                * nst[statvfs.F_FRSIZE] / my_bsize
            st.f_bavail += nst[statvfs.F_BAVAIL] \
                * nst[statvfs.F_FRSIZE] / my_bsize
            st.f_files  += nst[statvfs.F_FILES]
            st.f_ffree  += nst[statvfs.F_FFREE]

        return st

    class UnfsFile(object):
        """
        File object for UNFS.
        Handles opening, reading, writing, flushing and fstat.
        """

        def __init__(self, path, flags, *mode):
            """
            Initialise new file object.
            Try to find an existing file first on any of the nodes.
            If not found, create a new one, but only if 'w' or 'a' in the mode.
            Opens resulting file.
            """

            newPath = None

            # try to find existing file first
            for node in unfsNodes:
                try:
                    os.stat(node + path)
                    newPath = node + path
                    logging.critical('found file: %s' % newPath)
                    break
                except OSError:
                    logging.debug('%s does not exist' % newPath)

            m = flag2mode(flags)

            # if no file exists, choose random to write
            if 'w' in m or 'a' in m:
                # find new nodes here
                findNewNodes()
                if not newPath:
                    newPath = unfsRandom() + path
                    logging.critical('new file: %s' % newPath)

            self.path = newPath
            self.file = os.fdopen(os.open(self.path, flags, *mode), m)
            self.fd = self.file.fileno()

        def read(self, length, offset):
            """
            Read from self.file
            """

            self.file.seek(offset)
            return self.file.read(length)

        def write(self, buf, offset):
            """
            Write buf to self.file.
            """

            self.file.seek(offset)
            self.file.write(buf)
            return len(buf)

        def release(self, flags):
            """
            Close file.
            """

            logging.debug('release on %s with flags:%s' % (self.fd, flags))
            self.file.close()

        def _fflush(self):
            """
            Calls flush on self.file, if file is opened in 'a' or 'w' modes.
            """

            logging.debug('_fflush on %s' % self.fd)
            if 'w' in self.file.mode or 'a' in self.file.mode:
                self.file.flush()

        def flush(self):
            """
            Calls self.__flush, closes a dupe fd for current file.
            I guess closing a dupe of the file leaves the file open, but writes
            data out.
            """

            logging.debug('flush on %s' % self.fd)
            self._fflush()
            os.close(os.dup(self.fd))

        def fgetattr(self):
            """
            os.fstat wrapper for current file descriptor.
            """

            logging.debug('fgetattr on %s' % self.fd)
            return os.fstat(self.fd)

        def ftruncate(self, length):
            """
            Truncate a file to length bytes.
            """

            logging.debug('ftruncate, len:%s' % length)
            self.file.truncate(length)

        def lock(self, cmd, owner, **kw):
            """
            Lock file? Dunno.
            """

            logging.debug('lock: %s %s %s' % (cmd, owner, kw))
            return -errno.EINVAL

    # ignore args differ from overridden method since we call it directly.
    # also ignore 'magic' complaint
    # pylint: disable-msg=W0221
    def main(self, *a, **kw):
        """
        Main entry point. Mounts filesystem and daemonizes.
        """

        self.file_class = self.UnfsFile
        return Fuse.main(self, *a, **kw)
    # pylint: enable-msg=W0221


if __name__ == '__main__':
    usage = ""

    findNewNodes()

    server = UNFS(version="%prog " + fuse.__version__,
                     usage=usage,
                     dash_s_do='setsingle')

    server.parse(errex=1)
    server.main()

def go():
    """
    Start from some other script.
    """

    cmd = 'python %s %s' % (__file__, mountPoint)
    os.system(cmd)

def stop():
    """
    Stop from some other script.
    """

    os.system('fusermount -u %s 2>/dev/null' % mountPoint)
