"""
FL Studio MCP Controller Package

This package provides enhanced MIDI control surface integration for FL Studio.
"""

# Make all the public functions available at the package level
from device_FLStudioMCPController import (
    OnInit, OnDeInit, OnMidiMsg, OnIdle, OnTransport, OnTempoChange,
    RandomizeAllChannelColors, RandomizeSelectedChannelColors,
    AnimationSetup, NextAnimationFrame, RunSmoothAnimation, StopSmoothAnimation,
    RainbowPattern, ColorGroups, RandomColors, ColorByType, GradientPreset,
    RunTests
) 