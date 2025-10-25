# Performance Benchmarks

This directory contains reproducible benchmark scripts and baseline measurements for tracking performance trends.

## Structure

- `baselines/` - Baseline measurements for comparison
- `scripts/` - Benchmark execution scripts
- `reports/` - Weekly automated benchmark reports

## Running Benchmarks

```bash
# Run all benchmarks
./scripts/run_all.sh

# Run specific benchmark
./scripts/run_benchmark.sh <benchmark_name>
```

## Adding New Benchmarks

1. Create a script in `scripts/` following the naming convention `bench_<feature>.sh`
2. Document the benchmark purpose, methodology, and expected baseline
3. Add baseline measurement to `baselines/<feature>.json`
4. Update this README with usage instructions

## Performance Budgets

Per the constitution:

- Interactive actions: p95 < 200ms
- Background batch jobs: p99 < 2s
- Memory per process: < 100MB steady-state
- Scalability: 10k concurrent trivia sessions

## Trend Monitoring

Weekly automated runs produce trend reports. Three consecutive degradations trigger a mandatory investigation task.
