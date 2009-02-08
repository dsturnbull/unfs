"""
UNFS tests.
"""

import os
import md5
import stat
import random
import popen2
import shutil
import threading
import time
import unittest
import unfs

class TestUnfs(unittest.TestCase):
    """
    Main UNFS test case class.
    """

    def setUp(self):
        """
        Setup test data dir, mountpoint, node mountpoint, mount nodes and start
        UNFS.
        """

        # setup env
        self.testDir = os.getcwd() + '/testdata'
        unfs.base = self.testDir
        unfs.mountPoint = self.testDir + '/unfs'
        unfs.nodeMountPoint = self.testDir + '/fs'

        # test data
        self.testFile = os.getcwd() + '/test/blah.txt'
        self.testFileDest = unfs.mountPoint + '/blah.txt'
        self.testBigFileDest = unfs.mountPoint + '/bigfile'
        self.tar = os.getcwd () + '/test/linux-2.6.23.tar.gz'

        # make sure unfs is stopped
        unfs.stop()

        # clean old testdir
        os.system('rm -rf %s' % self.testDir)
        os.mkdir(self.testDir)

        # make sure mountpoint exists
        # set mountpoint locally for testing
        if not os.path.exists(unfs.mountPoint):
            os.mkdir(unfs.mountPoint)

        # nodes
        os.mkdir(unfs.nodeMountPoint)

        # local nodes
        self.nodes = {
            't1':unfs.nodeMountPoint + '/t1',
            't2':unfs.nodeMountPoint + '/t2',
            't3':unfs.nodeMountPoint + '/t3',
            't4':unfs.nodeMountPoint + '/t4',
        }

        for nodeName, nodePath in self.nodes.iteritems():
            os.mkdir(nodePath)

        # t1 has some data that noone else has
        # t3 has some data in a dir that t1 has
        os.mkdir(unfs.nodeMountPoint + '/t1/media')
        os.mkdir(unfs.nodeMountPoint + '/t1/media/tv')
        shutil.copyfile(self.tar, unfs.nodeMountPoint + '/t1/media/tv/sdf.avi')

        os.mkdir(unfs.nodeMountPoint + '/t3/media')
        os.mkdir(unfs.nodeMountPoint + '/t3/media/music')
        shutil.copyfile(self.tar, unfs.nodeMountPoint + '/t3/media/music/mp3')

        # remote fs nodes
        #self.remoteNodes = {
        #    'triton':'triton:/export/unfs',
        #    'nereid':'nereid:/giga/unfs',
        #    'romulus':'romulus:/rom/unfs',
        #}
        #for nodeName, nodePath in self.nodes.iteritems():
        #    self.mount(nodePath, unfs.nodeMountPoint + '/' + nodeName)
        #    self.assertTrue(self.mounted(nodePath, \
        #        unfs.nodeMountPoint + '/' + nodeName))

        # start unfs
        self.unfs_start()

    def tearDown(self):
        """
        Stop UNFS, remove mountpoint, node mountpoint, unmount nodes, remove
        each node mountpoint, remove test dir.
        """

        # stop unfs
        self.unfs_stop()

        # remove unfs mountpoint
        os.rmdir(unfs.mountPoint)

        # remove test data
        os.unlink(unfs.nodeMountPoint + '/t1/media/tv/sdf.avi')
        os.rmdir(unfs.nodeMountPoint + '/t1/media/tv')
        os.rmdir(unfs.nodeMountPoint + '/t1/media')
        os.unlink(unfs.nodeMountPoint + '/t3/media/music/mp3')
        os.rmdir(unfs.nodeMountPoint + '/t3/media/music')
        os.rmdir(unfs.nodeMountPoint + '/t3/media')

        # remove fs nodes
        for nodeName, nodePath in self.nodes.iteritems():
            os.rmdir(nodePath)

        # unmount remote
        #for nodeName, nodePath in self.remoteNodes.iteritems():
        #    self.unmount(nodePath, unfs.nodeMountPoint + '/' + nodeName)
        #    self.assertFalse(self.mounted(nodePath, \
        #        unfs.nodeMountPoint + '/' + nodeName))

        # remove fs mp
        os.rmdir(unfs.nodeMountPoint)

        # remove test dir
        os.rmdir(self.testDir)

    def unfs_start(self):
        """
        Start UNFS.
        """

        unfs.go()

    def unfs_stop(self):
        """
        Stop UNFS.
        """

        unfs.stop()
        time.sleep(1)

    def testNodesExist(self):
        """
        Test node paths exist.
        """

        for nodeName, nodePath in self.nodes.iteritems():
            self.assertTrue(os.path.exists(nodePath))

    def testUNFSMounted(self):
        """
        Grep /etc/mtab for evidence.
        """

        mtab = open('/etc/mtab', 'r').readlines()
        mps = {}
        for line in mtab:
            device, mp, mpType, mpArgs = line.split(' ', 3)
            mps[mp] = line.split(' ', 3)

        self.assertTrue(mps.has_key(unfs.mountPoint))

    def testReaddir(self):
        """
        Test ls -la on empty dir.
        """

        dot = os.stat(unfs.mountPoint + '/.')
        dotdot = os.stat(unfs.mountPoint + '/..')
        # self.rt.assertResponseEquals(self, self._testMethod, [dot, dotdot])

    def testCopyFile(self):
        """
        Copy a file to unfs.mountPoint, read it back, compare.
        """
        
        shutil.copyfile(self.testFile, self.testFileDest)

        orig = os.stat(self.testFile)
        copy = os.stat(self.testFileDest)

        statsToCompare = [stat.ST_MODE, stat.ST_NLINK, stat.ST_UID,
            stat.ST_GID, stat.ST_SIZE, stat.ST_ATIME]

        for st in statsToCompare:
            self.assertEqual(orig[st], copy[st])

        os.unlink(self.testFileDest)

    def testMkdir(self):
        """
        mkdir
        """

        testDir = unfs.mountPoint + '/testDir'
        os.mkdir(testDir)
        self.assertTrue(os.path.isdir(testDir))

        shutil.copy(self.testFile, testDir + '/blah.txt')
        self.assertTrue(os.path.isfile(testDir + '/blah.txt'))
        os.unlink(testDir + '/blah.txt')

        os.rmdir(testDir)

    def testABigFile(self):
        """
        big file, stress test kinda thing
        """

        bufSize = 1024 * 1024
        totalSize = bufSize * 100
        inFile = open('/dev/zero', 'r')
        outFile = open(self.testBigFileDest, 'w')

        start = time.time()
        bytes = 0
        while True:
            buf = inFile.read(bufSize)
            outFile.write(buf)
            bytes += len(buf)
            if bytes == totalSize:
                break

        inFile.close()
        outFile.close()

        end = time.time()
        os.unlink(self.testBigFileDest)

        timeTaken = float(end - start)
        mb = bytes/1024/1024
        mbs = bytes/1024/1024/float(end - start)
        self.assert_(mbs > 10)

    def testNodeDistrib(self):
        """
        Extract proz, stress test, make sure each node has at least 1/8 of tot.
        """

        os.system('tar zxf %s -C %s' % (self.tar, unfs.mountPoint))

        r, w, e = popen2.popen3('du --max-depth=1 %s' % \
            unfs.nodeMountPoint)

        sizes = []
        for line in r.readlines():
            size, _ = line.split('\t')
            sizes.append(int(size.replace('K', '')))
        r.close()
        w.close()
        e.close()

        nodeMinSize = os.stat(self.tar)[stat.ST_SIZE]/1024/8
        for size in sizes:
            self.assert_(size > nodeMinSize)

        os.system('rm -rf %s/%s' % (
            unfs.mountPoint,
            os.path.basename(self.tar).replace('.tar.gz', '')),
        )

    def testLock(self):
        """
        Lock a node for 2 seconds, ensure wait time > 2 seconds
        """

        # FIXME: not implemented yet, need to think more
        a = threading
        return

        #unfsLock = None
        #threading
        #t = unfsLock(unfs.nodeMountPoint)
        #t.start()

        #start = time.time()
        #shutil.copy(self.testFile, self.testFileDest)
        #os.unlink(self.testFileDest)
        #end = time.time()

        #print (end - start)
        #t.join()

    def sumFile(self, testFile):
        """
        helper method, md5 sum of file
        """

        m = md5.new()
        fp = open(testFile, 'r')
        while True:
            d = fp.read(8192)
            if not d:
                break
            m.update(d)
        fp.close()

        return m.hexdigest()

    def statFileCtime(self, fileName):
        """
        helper method, return ctime for file, from 'stat' program
        """
        r, w, e = popen2.popen3('stat %s | grep Change | awk \'{print $3}\'' \
            % fileName)
        return r.readlines()[0].strip()

    def testRsync(self):
        """
        Test rsync of a dir. Ensure files changed in subsequent run is 0.
        """
        
        # FIXME: rsync updates files even though files are identical
        rsyncDir = '/usr/bin'
        for i in range(0, 5):
            r, w, e = popen2.popen3(
                'rsync -avx %s %s/bin | wc -l' % (
                    rsyncDir,
                    unfs.mountPoint,
                )
            )
            output = int(r.readlines()[0].strip())

            for testFile in os.listdir(rsyncDir):
                try:
                    origFile = rsyncDir + '/' + testFile
                    copyFile = unfs.mountPoint + '/bin/%s/%s' % (
                        os.path.basename(rsyncDir),
                        os.path.basename(testFile)
                    )
                    orig = copy = {}

                    orig['stat'] = self.statFileCtime(origFile)
                    copy['stat'] = self.statFileCtime(copyFile)

                    orig['file'] = testFile
                    copy['file'] = testFile

                    orig['md5'] = self.sumFile(origFile)
                    copy['md5'] = self.sumFile(copyFile)

                    orig['mode'] = os.lstat(origFile)
                    copy['mode'] = os.lstat(copyFile)

                    orig['mtime'] = os.lstat(origFile)[stat.ST_MTIME]
                    copy['mtime'] = os.lstat(copyFile)[stat.ST_MTIME]

                    if orig != copy:
                        print orig, copy

                except Exception, why:
                    link = stat.S_ISLNK(os.lstat(origFile)[stat.ST_MODE])
                    if not link:
                        print os.lstat(origFile)

        os.system('rm -rf %s/bin' % unfs.mountPoint)

    def createManyFiles(self, numFiles, prefix='/'):
        """
        Helper for other tests. Creates random files
        """

        if not os.path.exists(prefix):
            os.mkdir(unfs.mountPoint + prefix)

        files = []
        for i in range(0, numFiles):
            fileName = unfs.mountPoint + prefix + \
                ''.join(random.sample('1234567890ABCDEF', 16)) + str(i)
            files.append(fileName)

            data = open('/dev/urandom', 'r').read(1024 * 10)
            fp = open(fileName, 'w')
            fp.write(data)
            fp.close()

        return files

    def deleteManyFiles(self, files, prefix=None):
        """
        helper method for above: deleted created files and prefix dir
        """

        for fileName in files:
            os.unlink(fileName)
        if prefix:
            os.rmdir(unfs.mountPoint + prefix)

    def testManyFiles(self):
        """
        Write a shitload of files and make sure they appear.
        """

        files = self.createManyFiles(1000)
        self.deleteManyFiles(files)

    def testManyFilesRsync(self):
        """
        rsync random files
        """

        # FIXME: sometimes it thinks files/ needs to be updated
        expected = [106, 4, 4, 4, 4]

        files = self.createManyFiles(5000, '/files/')
        for i in range(0, 5):
            r, w, e = popen2.popen3('rsync -avx %s/files %s/newfiles | wc -l' \
                % (unfs.mountPoint, unfs.mountPoint)
            )
            #output = ''.join(r.readlines())
            output = int(r.readlines()[0])
            #self.assertEqual(output, expected[i])

        self.deleteManyFiles(files, '/files/')
        os.system('rm -rf %s/newfiles' % unfs.mountPoint)

unittest.main()
