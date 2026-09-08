# Jodrell Anomaly Scanner
-------------------------


An experimental open-source tool for identifying unusual pulse-profile morphology in archival pulsar observations.

The scanner compares observations of the same pulsar, prioritising observations made at similar frequencies, and ranks profiles that differ significantly from their comparison observations.

The purpose is **candidate discovery and human investigation**, not automated scientific classification.

## What it does
- Retrieves pulsar profile data from the Jodrell Bank EPN archive
- Compares observations of the same pulsar
- Prioritises same-frequency observations
- Measures pulse-profile morphology differences
- Scores and ranks potentially unusual observations
- Produces visual comparisons for human review

## Important

A detected anomaly is **not necessarily an astronomical discovery**.

Differences can result from radio-frequency interference, instrumentation, calibration, observing conditions, frequency-dependent pulsar behaviour, or data-processing artefacts.

The scanner deliberately does not attempt to explain what an anomaly is. Interpretation and scientific validation should be performed by astronomers.

## Status

This is an experimental research prototype.

Version 0.3 is currently focused on archival EPN pulse-profile data. Future development may incorporate additional data sources and feedback from professional astronomers.

## Data

The project uses data available through the Jodrell Bank / University of Manchester EPN pulsar archive.

Data remain subject to the licensing and copyright conditions of their original authors and repositories.

## License

The software in this repository is released under the MIT License.
