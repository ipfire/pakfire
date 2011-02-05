#!/usr/bin/python

# XXX Maybe we could do this with something like
# libarchive to make it really fast.

import grp
import os
import pwd
import stat
import time

def ftype(mode):
    if stat.S_ISBLK(mode):
        return "b"
    elif stat.S_ISCHR(mode):
        return "c"
    elif stat.S_ISDIR(mode):
        return "d"
    elif stat.S_ISREG(mode):
        return "-"
    elif stat.S_ISFIFO(mode):
        return "p"
    elif stat.S_ISLINK(mode):
        return "l"
    elif stat.S_ISSOCK(mode):
        return "s"
    return "?"

def rwx(mode):
    ret = ""
    if mode & stat.S_IRUSR:
        ret += "r"
    else:
        ret += "-"

    if mode & stat.S_IWUSR:
        ret += "w"
    else:
        ret += "-"

    if mode & stat.S_IXUSR:
        ret += "x"
    else:
        ret += "-"

    return ret

def fmode(mode):
    ret = ftype(mode)
    ret += rwx((mode & 0700) << 0)
    ret += rwx((mode & 0070) << 3)
    ret += rwx((mode & 0007) << 6)
    return ret

class CpioError(Exception):
    pass


class CpioEntry(object):
    def __init__(self, hdr, archive, offset):
        self.archive = archive
        self.hdr = hdr

        self.offset  = offset + 110 + self.namesize
        self.offset += (4 - (self.offset % 4)) % 4
        self.current = 0

        self.closed = False

        if len(self.hdr) < 110:
            raise CpioError("Header too short.")

        if not self.hdr.startswith("070701") and not self.hdr.startswith("070702"):
            raise CpioError("Invalid header: %s" % self.hdr[:6])

    def close(self):
        self.closed = True

    def flush(self):
        pass # noop

    def read(self, size=None):
        """Read data from the entry.

        Keyword arguments:
        size -- Number of bytes to read (default: whole entry)
        """
        if self.closed:
            raise ValueError("Read operation on closed file.")

        self.archive.file.seek(self.offset + self.current, os.SEEK_SET)

        if size and size < self.size - self.current:
            ret = self.archive.file.read(size)
        else:
            ret = self.archive.file.read(self.size - self.current)
        self.current += len(ret)
        return ret

    def seek(self, offset, whence=0):
        """Move to new position within an entry.

        Keyword arguments:
        offset -- Byte count
        whence -- Describes how offset is used.
        0: From beginning of file
        1: Forwards from current position
        2: Backwards from current position
        Other values are ignored.
        """
        if self.closed:
            raise ValueError("Seek operation on closed file.")

        if whence == os.SEEK_SET:
            self.current = offset
        elif whence == os.SEEK_REL:
            self.current += offset
        elif whence == os.SEEK_END:
            self.current -= offset

        self.current = min(max(0, self.current), self.size)

    def tell(self):
        """Get current position within an entry"""
        if self.closed:
            raise ValueError("Tell operation on closed file.")
        return self.current

    def __repr__(self):
        return "<CpioEntry %s 0x%s>" % (self.name, self.checksum,)

    @property
    def checksum(self):
        return int(self.hdr[102:110], 16)

    @property
    def devmajor(self):
        return int(self.hdr[62:70], 16)

    @property
    def devminor(self):
        return int(self.hdr[70:78], 16)

    @property
    def gid(self):
        return int(self.hdr[30:38], 16)

    @property
    def inode(self):
        return int(self.hdr[6:14], 16)

    @property
    def mode(self):
        return int(self.hdr[14:22], 16)

    @property
    def mtime(self):
        return int(self.hdr[46:54], 16)

    @property
    def name(self):
        end = 110 + self.namesize - 1
        return self.hdr[110:end]

    @property
    def namesize(self):
        return int(self.hdr[94:102], 16)

    @property
    def nlinks(self):
        return int(self.hdr[38:46], 16)

    @property
    def rdevmajor(self):
        return int(self.hdr[78:86], 16)

    @property
    def rdevminor(self):
        return int(self.hdr[86:94], 16)

    @property
    def size(self):
        return int(self.hdr[54:62], 16)

    @property
    def uid(self):
        return int(self.hdr[22:30], 16)


class CpioArchive(object):
    def __init__(self, filename):

        self.filename = filename
        self.file = open(self.filename, "r")
        self.__readfile()

        self.closed = False

    def close(self):
        if self.closed:
            return
        self.closed = True

        self.file.close()

    def __readfile(self):
        if not self.file:
            raise CpioError("File was not yet opened.")

        self._entries = []
        sposition = self.file.tell()
        hdr = self.file.read(110)
        while hdr:
            namelen = int(hdr[94:102], 16) # Length of the name
            hdr += self.file.read(namelen)
            ce = CpioEntry(hdr, self, sposition)
            if ce.name == "TRAILER!!!":
                return
            self._entries.append(ce)

            self.file.seek((4 - (self.file.tell()-sposition) % 4) % 4, os.SEEK_CUR)
            self.file.seek(ce.size, os.SEEK_CUR)
            self.file.seek((4 - (self.file.tell()-sposition) % 4) % 4, os.SEEK_CUR)

            sposition = self.file.tell()
            hdr = self.file.read(110)
        else:
            raise CpioError("Premature end of headers.")

    @property
    def entries(self):
        return sorted(self._entries)

    @property
    def size(self):
        return os.path.getsize(self.filename)

    def ls(self):
        for x in self.entries:
            print x.name

    def ll(self):
        for x in self.entries:
            print "%s %s %s %s %9d %s %s" % \
                (fmode(x.mode),
                 x.nlinks,
                 pwd.getpwuid(x.uid)[0],
                 grp.getgrgid(x.gid)[0],
                 x.size,
                 time.strftime("%Y-%m-%d %H:%M", time.localtime(x.mtime)),
                 x.name,)

    def get(self, item):
        for x in self._entries:
            if x.name == item:
                return x
        raise KeyError("No such file or directory.")

    def __getitem__(self, item):
        x = self.get(item)
        x.seek(0)
        return x.read()
