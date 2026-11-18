# Prooflane research materials

This archive accompanies the revised research brief. It contains generated files, an executable comparison, a saved five-class ByteCNN checkpoint, per-file results, figures and saved scheduling results with a trace-generation command.

## Reproduce the offline CNN experiment

The archived run used macOS on Apple ARM64, Python 3.13.7, PyTorch 2.15.0 and NumPy 2.5.5 with two CPU threads. The plots were generated with Matplotlib 3.10.9. After extracting the archive, use a fresh working copy to preserve the recorded results. From its root:

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install torch==2.15.0 numpy==2.5.5 matplotlib==3.10.9
    python run_study.py
    python check_equations.py
    python plot_results.py

The runner imports ml/cnn/model.py and ml/cnn/infer.py, unchanged copies from the project. It uses the experiment's shared comparison harness and format labels. The study checkpoint belongs in this research folder. It predicts benign fixture formats. It was not installed as an application release model. The baseline is nearest training-class median byte length. Same-class generated files share templates. Class order in all confusion matrices is TXT, CSV, JSON, PDF, PNG.

The runner writes a new checkpoint, loss curves, test predictions and environment metadata to cnn-results/. Numerical results across PyTorch/hardware versions may vary. Latencies are local observations and will vary between runs. The single-item timing excludes preprocessing, I/O and checkpoint loading.

## Data and checks

- fixtures/ contains 200 harmless synthetic files from the project's v2 dataset. Each of the five formats has 40 unique hashes. cnn-results/splits.csv lists the 120 training, 40 validation and 40 test files, including hashes and lengths.
- Generate the full trace from the repository root with `python -m benchmarks.generate --output research/scheduling --seed 17`. The resulting scheduling/workload.jsonl is the full 3,600-row synthetic seed-17 job trace. It contains timestamps, numeric job features, strictly earlier graph context and generated duration and demand targets. The workload generator used a fixed FIFO history. The two-worker simulation tested policies on 720 later jobs. The original scheduling/README.md identifies the training pipeline in the full application repository. The repository includes the trace generator, training code, manifests and measured outputs. Follow the scheduling README to repeat the full scheduler experiment.
- gateway/ contains unchanged project snapshots of the release-predicate and job-ranking functions. check_equations.py executes them without the database or cloud services.
- figures/ contains the system and model diagrams as vector PDF and SVG, and the measured scheduling and CNN figures as vector PDF and PNG.
