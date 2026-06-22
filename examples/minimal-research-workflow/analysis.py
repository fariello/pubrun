#!/usr/bin/env python3
"""Minimal research workflow using pubrun.

Demonstrates tracking a simple synthetic scientific analysis:
1. Generating synthetic 2D data points.
2. Fitting a linear regression model.
3. Writing a model report (JSON) and prediction results (CSV).
"""
import random
import math
import pubrun

def main():
    print("Initializing minimal research workflow analysis...")
    
    # 1. Load/Generate data phase
    with pubrun.phase("data_generation"):
        # Set seed for reproducibility
        random.seed(42)
        
        # Generate synthetic data with some noise: y = 2.5 * x + 1.0 + noise
        n_samples = 100
        x_values = [random.uniform(-5.0, 5.0) for _ in range(n_samples)]
        noise = [random.normalvariate(0.0, 1.0) for _ in range(n_samples)]
        y_values = [2.5 * x + 1.0 + n for x, n in zip(x_values, noise)]
        
        # Write input data as a raw CSV artifact
        csv_data = "x,y\n" + "\n".join(f"{x:.4f},{y:.4f}" for x, y in zip(x_values, y_values))
        pubrun.artifact("raw_data.csv", csv_data)
        pubrun.annotate("Generated synthetic dataset.", n_samples=n_samples)

    # 2. Model training/fitting phase
    with pubrun.phase("model_fitting"):
        # Fit a simple linear regression model (OLS): y = w * x + b
        mean_x = sum(x_values) / n_samples
        mean_y = sum(y_values) / n_samples
        
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values))
        den = sum((x - mean_x) ** 2 for x in x_values)
        
        w = num / den
        b = mean_y - w * mean_x
        
        pubrun.annotate("Linear model fitting complete.", slope=w, intercept=b)

    # 3. Model evaluation phase
    with pubrun.phase("model_evaluation"):
        y_pred = [w * x + b for x in x_values]
        mse = sum((y_true - y_p) ** 2 for y_true, y_p in zip(y_values, y_pred)) / n_samples
        rmse = math.sqrt(mse)
        
        # Save evaluation metrics as a structured report
        report_data = {
            "model_type": "LinearRegression",
            "coefficients": {
                "slope": w,
                "intercept": b
            },
            "metrics": {
                "mse": mse,
                "rmse": rmse
            }
        }
        pubrun.report("evaluation_metrics", report_data)
        
        # Write predictions as a CSV artifact
        pred_csv = "x,y_true,y_pred\n" + "\n".join(
            f"{x:.4f},{y_t:.4f},{y_p:.4f}" for x, y_t, y_p in zip(x_values, y_values, y_pred)
        )
        pubrun.artifact("predictions.csv", pred_csv)
        pubrun.annotate("Evaluation complete and artifacts saved.")

    print(f"Analysis complete. Fitted line: y = {w:.4f} * x + {b:.4f} (RMSE: {rmse:.4f})")

if __name__ == "__main__":
    main()
