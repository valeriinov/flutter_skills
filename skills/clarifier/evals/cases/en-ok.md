<!-- expect: ok -->
# The nightly build is faster

The nightly build now takes five minutes instead of twenty. The script clears the cache before each run.

<details><summary>Why it was slow</summary>

The cache grew until the disk was full, and the build waited for a manual restart.
</details>
