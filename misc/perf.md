Capturing performance data with perf
====================================

For best results the C source should be built with `-g -O0`.

Run the server, record performance events with `-F` frequency `997 Hz`, `-a` all processes and `-g` take stack info.

```
python examples/simple/simple.py -p c & \
perf record -F 997 -a -g -- sleep 59 & \
sleep 1 && ./wrk -c 100 -t 1 -d 60 http://localhost:8080 &
```

Write data to a text file filtering for pid `2836` (should be server process)

```
perf script --pid 2836 > out.perf
```

Remove address info to make graphs easier to read

```
python cleanup_script.py out.perf > out2.perf
```

Visualize data with a flame graph
=================================

```
./stackcollapse-perf.pl out2.perf > out.folded
./flamegraph.pl out.folded > test.svg
```
