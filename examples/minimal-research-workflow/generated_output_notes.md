# Generated Run Directory Outputs

After executing `analysis.py`, a new run directory is created under `./runs/pubrun-XXXXXXXX-XXXXXX/`. Below is a breakdown of the generated files:

## Core Metadata Files
- `manifest.json`: Contains the complete, structured metadata for the run (hardware, OS, git state, loaded packages, environment variables, annotations, reports, and registered artifacts).
- `config.resolved.json`: The fully resolved configuration settings used for this run.
- `stdout.log`: A timestamped record of all console output (stdout/stderr) printed during the run.

## Custom Reports
- `evaluation_metrics.json`: Created via `pubrun.report("evaluation_metrics", report_data)`. Contains the structured model coefficients (slope, intercept) and performance metrics (MSE, RMSE).

## Registered Artifacts
- `raw_data.csv`: Created via `pubrun.artifact("raw_data.csv", csv_data)`. Contains the 100 synthetic data points generated for training the model.
- `predictions.csv`: Created via `pubrun.artifact("predictions.csv", pred_csv)`. Contains the inputs (`x`), target outputs (`y_true`), and predicted outputs (`y_pred`) for verification.
