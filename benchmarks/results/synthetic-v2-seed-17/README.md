# Measured synthetic v2 run — seed 17

These files were copied from the host-generated `artifacts/results-v2` report and `artifacts/models` manifests after actual container training on 13 November 2026. They contain measured values, not example results. Weights remain in local `artifacts/models` and are not included here.

- Dataset SHA-256: `865049578a32926789c96334124c38339c61f0c609eba8007318d5829e3a3039`.
- Purged temporal training/validation/test: 1,800/240/720 rows; 300-second demand horizon.
- Independent LightGBM and TGN alternatives; seed 17; two simulated workers.
- TGN: ten epochs, validation-selected weights from epoch 5.
- [results.json](results.json): complete comparison, inference measurements and limitations.
- [results.csv](results.csv): scheduler metrics.
- [lightgbm-manifest.json](lightgbm-manifest.json) and [tgn-manifest.json](tgn-manifest.json): actual checkpoint hashes, prediction metrics and training logs.

LightGBM had the lowest mean queue wait (676.681 s); EDF missed the fewest deadlines (595/720). TGN had mean wait 685.039 s and 633 misses, slightly worse than FIFO (685.001 s, 630 misses). Both learned models substantially underpredicted held-out demand. Lower TGN prediction MAE did not translate into a scheduling advantage here.

Comparison inference took 0.082292 s for LightGBM and 111.574990 s for TGN over 720 jobs. It is measured separately and not added to queue-delay simulation. This is one synthetic run with arrival-time cached predictions; it is not a real scanner/resource benchmark, measured download latency, security fault evaluation, uncertainty estimate, or evidence of real-world generalization.

Reproduce training and comparison with the documented research container:

```sh
docker compose --profile research run --rm --no-deps research python -m ml.pipeline --seed 17 --epochs 10
```

Dependencies are currently bounded by version ranges, not a fully locked environment; timing and exact numerical reproducibility across versions/hardware are not guaranteed. The recorded host used CPU Torch 2.15.0, PyG 2.8.1 and LightGBM 4.7.0 on ARM64. The report and weight hashes identify this actual run. Do not overwrite it with a rerun and describe it as the same measurement.
