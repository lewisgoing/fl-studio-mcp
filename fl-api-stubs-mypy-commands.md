### Direct mypy commands (not just through uv)

```bash
# Check a specific file
mypy fl_studio_controller/device_flstudiocontroller.py

# Check the entire project with more verbose output
mypy --verbose .

# Check with specific config file
mypy --config-file mypy.ini .

# Check with plugin explicitly activated
mypy --plugins fl_studio_api_stubs.mypy_plugin .
```

### Test imports in Python interpreter

```bash
# Start Python interpreter
python

# Then try importing FL Studio modules to check they're recognized
>>> import channels
>>> import mixer
>>> import transport
>>> # If no error is raised, imports are working
>>> exit()
```

### Generate stub reports

```bash
# Generate a report of all stub modules available
mypy --show-traceback fl_studio_controller/device_flstudiocontroller.py

# Check what modules mypy recognizes
mypy --install-types
```

### Check typings with reveal-type

You can add `reveal_type()` calls in your code and run mypy to see what types are inferred:

```python
# Add this to your file
from typing import Any
import channels

# This will reveal the inferred type when you run mypy
reveal_type(channels.selectedChannel)  # type: ignore
```

Then run:
```bash
mypy fl_studio_controller/device_flstudiocontroller.py
```

The output will show you what type mypy thinks the function/variable has, which confirms the stubs are working.

These commands should help you verify that your FL Studio API stubs are properly installed and recognized by your development tools.