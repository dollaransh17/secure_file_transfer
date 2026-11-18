# Research methods and limitations

## Question and claim boundary

Investigate safety-constrained learning-assisted verification scheduling in a version-aware file-sharing system. Version/epoch/ACL enforcement is deterministic and independently testable. Workload prediction is optional. Existing TGN, GRU, attention, gradient boosting, SHA-256, versioned storage and authorized retrieval are established techniques. Integration is not evidence of a novel model or superior scheduling.

The supplied literature review recommends a scoped joint-failure benchmark and warns against substituting malware-family classification for binary detection or treating EMBER features as executable bytes. This implementation follows those restrictions. The newer user-specified TGN scheduling direction is an additional hypothesis rather than a claim established by that review.

## TGN-inspired implementation

`ml/temporal_gnn/model.py` implements learned node-type and edge-type embeddings, a two-layer message MLP, recurrent GRU memory, learned cosine elapsed-time encoding, bounded strictly-past neighborhood selection, PyTorch Geometric TransformerConv attention, joint context embeddings and two nonnegative Softplus workload heads.

At each prediction time, replay at most 128 strictly-past typed events from the shared `ml.context` input contract. Both node types, the edge type, elapsed time and an allowlisted event vector enter the message network. Event messages update recurrent node memories in chronological order. The same snapshot validation and `predict_context` method run in training and live inference. Unknown types, future or simultaneous events, non-finite inputs and inconsistent node types are rejected. Query adjacency includes at most 32 recent relevant edges.

Training differentiates the prediction loss through the complete bounded context replay, using log-scale Smooth L1 loss and gradient clipping. Each sample resets memory and replays its historical snapshot, so train/validation/test samples cannot inherit accidental state from another replay. This provides a manageable bounded TGN-inspired implementation rather than an unbounded production TGN service. It is computationally expensive and must be profiled before scaling. Ablations disable memory or graph attention.

Every actual scheduler selection now persists its tabular feature vector, attempt number, timestamp and typed graph snapshot. Both model inference and snapshot logging use the same feature builder. The application exporter consumes those recorded inputs, refuses legacy decisions without the current schema and waits until the 300-second demand label matures. It no longer reconstructs queue length from a subset of completed jobs. Full tensor training and live train/serve equivalence remain unexecuted because dependencies cannot be installed in this sandbox.

See the original [TGN paper](https://arxiv.org/abs/2006.10637) and [PyG TGN documentation](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.nn.models.TGNMemory.html) for prior methods. The implementation here uses a custom memory module and PyG attention, not PyG TGNMemory directly.

## LightGBM alternative

Two independently fitted LightGBM regressors share prediction-time features with TGN: log file size, queued age, deadline remaining, previous completed verification duration, recent authorized request count, queue length, attempt count and worker capacity. Hyperparameters are fixed, with seed 17 and no held-out tuning. Booster text files avoid arbitrary pickle loading. LightGBM and TGN are mutually exclusive scheduling strategies.

## Targets and splits

Duration is measured end-to-end worker processing time for genuine application exports. Generated workloads instead use explicitly parameterized synthetic durations; those are not observed ClamAV performance. Demand is the authorized request count within a 300-second horizon. Historical requests are features; future requests are labels only. A 60/20/20 temporal split purges training/validation rows whose target window crosses the next split. A `history_until < prediction_time` invariant rejects future or simultaneous feature records. Seeds, source digest, feature schema, split sizes, logs and test metrics are stored in manifests.

Duration metrics include MAE, RMSE and per-job inference time. Demand metrics include MAE and mean residual bias; the latter is only an aggregate calibration diagnostic, not a full count calibration study. More rigorous calibration bins, temporal drift strata and held-out workload-family evaluation remain necessary. No superiority claim is permitted based on training loss.

Early stopping is implemented for TGN using validation error and five-epoch patience. LightGBM currently uses a fixed estimator count and reports validation metrics. Ablations disable recurrent memory or graph attention. Real exports use recorded scheduling-time queue and worker-capacity snapshots; legacy jobs without those inputs are skipped rather than reconstructed.

## CNN boundary

`ml/cnn` contains a fixed 64 KiB byte-to-256×256 grayscale representation, small convolutional network, explicitly declared task/classes, training/validation checkpoint selection, loading and inference. Binary detection and family classification are distinct manifest task values. No compatible data or checkpoint was supplied, so CNN is disabled. It cannot bypass ClamAV or release evidence. A feature-only malware dataset is rejected by the manifest contract. License validation, deduplication, temporal splitting and held-out evaluation are researcher responsibilities; no detection effectiveness has been measured.

## Harmless dataset

The generator creates 200 TXT/CSV/JSON/PDF/PNG files, 20 scenario templates and ten seed variants each. It also creates 3,600 job samples across six synthetic low-demand, high-demand, burst and congestion regimes with changing file-size/cost distributions. It does not download malware or use private user data. Template definitions are saved as scenario metadata. The current conformance runner evaluates one independent specification case per template, not all 200 event schedules against the live application.

The independent oracle imports no application code. It computes expected permission/version/epoch/digest/freshness outcomes from scenario facts. The initial conformance adapter checks the application's pure release predicate against those facts. This is specification conformance, not proof of transactional gateway correctness. Several named failure templates currently reduce to the same final facts; a complete event-driven fault injector is still required.

## Current experiment runner

`benchmarks.run` pairs FIFO, EDF and rule-based scheduling on identical generated jobs, two workers and common deadline/aging overrides. It reports mean/P95 queue wait, deadline misses, utilization, total modeled verification time, peak backlog, wall-clock execution and CPU time. It writes machine-readable JSON/CSV. Its availability windows include low-demand idle periods, so overall utilization can remain low despite a severe burst backlog.

This runner does not yet compare trained ML schedulers, legitimate-download delay, all five integrity-monitoring policies, live object-store costs, duplicate event counts, peak RSS, inference cost or policy-invalid releases under real faults. There are no repeated-run confidence intervals or held-out family comparisons yet. Do not infer zero live policy-invalid releases from predicate conformance. The synthetic workload's deadlines are a common creation-relative offset; consequently FIFO and EDF can select the same order. This observed equality is retained rather than hidden.

## Required next experiments

Freeze dataset versions, explicit workload-family holdouts, capacity/deadline policies and matching measurement definitions. Collect actual scheduling snapshots and verify their live replay equivalence. Train both alternatives using identical causal periods and target maturity. Evaluate on unseen files/users and held-out workload regimes. Integrate their measured predictions into the paired simulator and then live PostgreSQL/MinIO/ClamAV runs. Compare periodic, event-driven, hybrid, always-verify and dependency-aware bounded repair with the same request schedules and resource budgets. Add repeated seeds and paired confidence intervals. Report negative outcomes and simple baseline wins.

## Sources used for protocol integration

The scanner client follows the official [ClamD INSTREAM protocol](https://docs.clamav.net/manual/Usage/ClamdProtocol.html). Claude integration uses the official [Python models API](https://platform.claude.com/docs/en/api/python/models) to validate configuration against account-supported models. These documentation checks do not constitute successful runtime integrations.
