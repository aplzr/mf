# 2025-10-27
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
Switching from `Path(DirEntry).stat().st_mtime` to `DirEntry.stat().st_mtime` (see issue [#19](https://github.com/aplzr/mf/issues/19))

- Numbers are `mf new` runtime duration with two configured search paths
- Both are on seperate mechanical drives on a Linux file server, mounted via SMB on the clients
- Total file volume ~17 TiB 

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

## Platform performance difference - unresolved
There's also a stark difference in `mf new` runtime duration depending on the platform on which it is called:

\[See table one entry up\]

I initially thought this was `DirEntry` caching on Windows but not on Linux (see entry above), but at the time of writing the implementation uses `Path.stat()` which never caches. Cause currently unknown - possibly SMB client implementation differences, network stack optimizations, or the differnce between WIFI and wired network (although the AP is very close and no network contention to speak of).

# 2025-10-29
## Platform performance difference - continued
I looked more into why running `mf new` takes so much longer on my Linux desktop compared to my Windows desktop. Initial situation was this:

- Two configured search paths
- Both are on separate mechanical drives on a Linux file server, mounted via SMB on the clients
- Total file volume ~17 TiB

Initial average `mf new` scan duration on Linux was almost 15 s, compared to 5.2 s on Windows. Optimization of the file scanning code in `mf` reduced this to 13.1 and 2.4 s, respectively. Nice, but on Linux nowhere near where I'd like it to be.

I ended up experimenting with SMB/CIFS protocol versions and caching parameters, then switched from SMB to NFS shares on the file server and repeated the parameter tweaking.

All numbers with a warm cache:

| Optimization Step | Average Time (seconds) | Time Saved (seconds) | Improvement (%) | Cumulative Improvement (%) |
|-------------------|------------------------|---------------------|-----------------|---------------------------|
| First implementation | 14.55 | - | - | - |
| Switch from Path.stat to DirEntry.stat | 13.08 | 1.47 | 10.1% | 10.1% |
| More aggressive SMB caching (vers=3.1.1, cache=loose, actimeo=86400) | 10.97 | 2.11 | 16.2% | 24.6% |
| Switch to NFS with standard caching | 3.74 | 7.22 | 65.9% | 74.3% |
| Aggressive NFS caching (acdirmin=60, acregmin=3600) | 1.82 | 1.92 | 51.4% | 87.5% |

**Final result: 8x faster than original (14.55s → 1.82s), now 24% faster than Windows (2.4s).**

Up to this point I had always been quite happy with SMB in my shared Windows/Linux environment, as both sides understand it, but these numbers make it absolutely clear that NFS is the way to go for Linux ↔ Linux file serving. The difference is particularly dramatic for metadata-heavy operations like directory scanning.

**Key takeaways:**
- SMB on Linux is significantly slower than on Windows for metadata operations
- NFS provides much better performance for Linux clients (65.9% improvement over optimized SMB)
- Aggressive attribute caching is safe and effective for read-only static content
- Using `acdirmin=60` allows new files to appear within 60 seconds while keeping fast scans