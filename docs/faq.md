# Frequently Asked Questions (FAQ) & Troubleshooting

This document covers common questions, best practices, and troubleshooting for developing
experiments and collecting research data with the Pupilio SDK.

---

## 1. General & Hardware Setup

### Q: Can I develop and debug my experiment scripts on a PC without the eye tracker connected?

**A:** Yes. Set `config.simulation_mode = True` when initializing `Pupilio`:

```python
from pupilio import Pupilio, DefaultConfig

config = DefaultConfig()
config.simulation_mode = True  # mouse cursor drives gaze coordinates
pupil_io = Pupilio(config=config)