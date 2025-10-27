## Caching `stat` info and `os.scandir`, `os.DirEntry`, and `pathlib.Path`
The list of files is currently built by traversing the search paths with `os.scandir`, then converting each resulting `DirEntry` object to `pathlib.Path` and calling `stat().st_mtime` to get the last modified time for sorting. This is much faster (around 5 s for all files on my two network search paths) than getting the file list with something other than `os.scandir` and then converting that to `pathlib.Path` followed by `stat().st_mtime` (around 26 s for the same file list).

I had assumed the reason for this difference is that `os.scandir` directly caches the stat info in its `DirEntry` objects and that this cached info is passed on when converting to `pathlib.Path`, so that the subsequent call to `stat().st_mtime` does not result in an additional syscall that needs to traverse the network. 

But looking at the [`pathlib.Path.stat` documentation](https://docs.python.org/3/library/pathlib.html#pathlib.Path.stat) reveals it never caches the stat info, so converting a `DirEntry` with cached info to `Path` means the cache is lost:

> Path.stat(*, follow_symlinks=True)
>
> Return an os.stat_result object containing information about this path, like os.stat(). The result is looked up at each call to this method.

Takeaways:
- `Path.stat` never caches.
- The 5 s vs 26 s difference suggests filesystem/network-level caching might 
be providing the speedup, not Python-level caching. Needs further investigation.
- In cases where `mtime` is needed I should grab it directly from `DirEntry.stat` (which I already have and which _might_ have a cached result), not from `Path(DirEntry).stat` (which always makes a syscall).

### `DirEntry.stat` caching behaviour
`DirEntry` doesn't always cache either - it mostly does on Windows, but never on Linux. As per the [scandir docs](https://docs.python.org/3/library/os.html#os.scandir):

> os.DirEntry.stat() always requires a system call on Unix but only requires one for symbolic links on Windows.

Note: [`Path` has started to cache some information in its new `info` attribute](https://docs.python.org/3/library/pathlib.html#pathlib.Path.info) starting in Python 3.14, but no stat info so far.

### Performance validation on Windows
Switching from `Path(DirEntry).stat().st_mtime` to `DirEntry.stat().st_mtime` (see issue [#19](https://github.com/aplzr/mf/issues/19)) (`mr new` runtime duration):

**Before**: 5199 ms average (warm cache)  
**After**: 2378 ms average (warm cache)  
**Improvement**: 2.2x speedup

This confirms that Windows `DirEntry` caching provides substantial benefits 
even with warm filesystem caches.

### Performance validation on Linux
Adding to the results above, running the same comparison on my Linux desktop I only see a slight improvement, with total runtime duration being 2.8 to 5.5 times that of the Windows desktop:

| Platform | Method | Time | Improvement |
|----------|---------|------|-------------|
| **Windows (wired)** | Path.stat | 5.2 s | - |
| **Windows (wired)** | DirEntry.stat | 2.4 s | **2.2x faster** |
| **Linux (WiFi)** | Path.stat | 14.6 s | - |
| **Linux (WiFi)** | DirEntry.stat | 13.1 s | **1.1x faster** |

The much smaller improvement is in line with `DirEntry` caching stat info on Windows, but always needing an additional syscall on Linux (which is effecively what the previous implementation was doing).

## Platform Performance Difference - Unresolved
There's also a stark difference in `mf new` runtime duration depending on the platform on which it is called:

\[See table one entry up\]

I initially thought this was `DirEntry` caching on Windows but not on Linux (see entry above), but at the time of writing the implementation uses `Path.stat()` which never caches. Cause currently unknown - possibly SMB client implementation differences, network stack optimizations, or the differnce between WIFI and wired network (although the AP is very close and no network contention to speak of).

