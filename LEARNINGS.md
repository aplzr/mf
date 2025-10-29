# About this document
I've started development on `mf` out of a personal need for a simple CLI tool that enables me to quickly find and play video files in my collection hosted on a file server in my local network. I wanted this because I was generally unhappy with tools like Kodi that pack a lot of stuff I don't need and are generally (to me) relatively cumbersome to use. I'd much rather use a text-based interface with high information density than scroll through endless pages of title cards with maybe 8 of them visible.

The basic functionality that satisfies this need was implemented pretty quickly, but then I got more ideas and wanted to streamline certain things a little more, so I started viewing `mf` development as more of a chance to learn new things and concepts in software development. I'm a self-taught programmer with a science background and would describe myself as a reasonably competent intermediate python programmer. But like many self-taughts coming from science, I was never formally introduced to many of the higher-order patterns of software development that are helpful for writing good software. So now I'm trying to fill a few of these gaps, have a little fun while doing so, and document things I've learned here in this file.

## LLM use
I'm having quite a bit of help from Copilot (in VSC) and Claude (in the browser). The way I'm using it is not to have it implement things for me, but rather review and critique the code that I'm writing by hand and give me starters on how to solve certain problems. I'm doing this in the browser as much as I can because the LLM not having access to my workspace forces me to think about how to frame problems and be precise in my questions. This way I can discover concepts and solutions that I wouldn't have been able to come up with myself while still doing a reasonable amount of legwork, which in turn means I'm learning something while progressing at a nice pace at the same time.

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

- Numbers are `mf new` scan duration with two configured search paths
- Both are on seperate mechanical drives on a Linux file server, mounted via SMB on the clients
- Total file volume ~17 TiB 

**Before**: 5199 ms average (warm cache)  
**After**: 2378 ms average (warm cache)  
**Improvement**: 2.2x speedup

This confirms that Windows `DirEntry` caching provides substantial benefits 
even with warm filesystem caches.

### Performance validation on Linux
Adding to the results above, running the same comparison on my Linux desktop I only see a slight improvement, with scan duration being 2.8 to 5.5 times that of the Windows desktop:

| Platform | Method | Time | Improvement |
|----------|---------|------|-------------|
| **Windows (wired)** | Path.stat | 5.2 s | - |
| **Windows (wired)** | DirEntry.stat | 2.4 s | **2.2x faster** |
| **Linux (WiFi)** | Path.stat | 14.6 s | - |
| **Linux (WiFi)** | DirEntry.stat | 13.1 s | **1.1x faster** |

The much smaller improvement is in line with `DirEntry` caching stat info on Windows, but always needing an additional syscall on Linux (which is effecively what the previous implementation was doing).

## Platform performance difference - unresolved
There's also a stark difference in `mf new` scan duration depending on the platform on which it is called:

\[See table one entry up\]

I initially thought this was `DirEntry` caching on Windows but not on Linux (see entry above), but at the time of writing the implementation uses `Path.stat()` which never caches. Cause currently unknown - possibly SMB client implementation differences, network stack optimizations, or the differnce between WIFI and wired network (although the AP is very close and no network contention to speak of).

# 2025-10-28
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
| Switch from `Path.stat` to `DirEntry.stat` | 13.08 | 1.47 | 10.1% | 10.1% |
| More aggressive SMB caching (`vers=3.1.1`, `cache=loose`, `actimeo=86400`) | 10.97 | 2.11 | 16.2% | 24.6% |
| Switch to NFS with standard caching | 3.74 | 7.22 | 65.9% | 74.3% |
| Aggressive NFS caching (`acdirmin=60`, `acregmin=3600`) | 1.82 | 1.92 | 51.4% | 87.5% |

**Final result: 8x faster than original (14.55s → 1.82s), now 24% faster than Windows (2.4s).**

Up to this point I had always been quite happy with SMB in my shared Windows/Linux environment, as both sides understand it, but these numbers make it absolutely clear that NFS is the way to go for Linux <-> Linux file serving. The difference is particularly dramatic for metadata-heavy operations like directory scanning.

**Key takeaways:**
- SMB on Linux is significantly slower than on Windows for metadata operations
- NFS provides much better performance for Linux clients (65.9% improvement over optimized SMB)
- Aggressive attribute caching is safe and effective for read-only static content
- Using `acdirmin=60` allows new files to appear within 60 seconds while keeping fast scans

# 2025-10-29
## Unit tests
Contrary to what I've written about using LLMs more as a personal tutor and not to have them do all the coding for me, today I've had Copilot set up a full unit test suite without me doing basically anything. I literally did not type a single character in any of those test definitions. I just told Copilot to write all tests that it can write without touching my code, let it install `pytest` and `pytest-cov`, let it add them to `pyproject.toml` as development dependencies with appropriate options and then let it have at it. Copilot wrote tests, checked coverage results to find out what was still missing, then added more tests, and so on. Sometimes it asked me if I would allow it to make small changes to `mf`'s code so it could test something more easily, and after each iteration it explained in detail which tests it had added, what was still missing, and asked whether to continue with more tests or do something else. After going back and forth like this for around 30 minutes, I had a suite of 65 tests covering 85% of my codebase. Pretty neat.

As I've said before, I generally try to avoid having LLMs do all the work, but writing tests feels like it might be an exception to that rule. I don't know what the opinion about LLM-generated tests is in professional circles, but my assumption is that driving up coverage with LLM-generated tests is not the worst thing to do in the world.

Let's go full circle and ask Claude about it:

> There's pragmatic acceptance but not enthusiasm.
> Most developers see LLM-generated tests as useful for boilerplate and scaffolding, but they require review because they often:
>
> - Test implementation details instead of behavior
> - Miss important edge cases while catching trivial ones
> - Create false confidence through high coverage numbers
>
> The consensus: helpful for getting started quickly, but don't commit them without reading and refining. They're seen as productivity boosters for grunt work, not replacements for thoughtful testing.

That sounds like fair criticism, and I will admit that I actually _did_ feel confident because of the high coverage my LLM-tests achieved and that I _didn't_ properly review them before comitting. I feel like it's not much of an issue for my personal use project, but I understand that the situation changes when the stakes are higher.

