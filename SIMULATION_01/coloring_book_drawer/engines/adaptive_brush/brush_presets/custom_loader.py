"""
Custom Brush Loader
=====================
Loads user-defined brush presets from JSON files.
"""

import json
import os
from typing import Optional
from ..config import (
    AdaptiveBrushConfig, PencilTipConfig, PaperConfig, PressureConfig,
    AccumulatorConfig, TipShape, PaperType
)
from .presets import BrushPreset, BrushPresets


class CustomBrushLoader:
    """Loads custom brush presets from JSON configuration files."""
    
    @staticmethod
    def load_from_file(filepath: str) -> Optional[BrushPreset]:
        """
        Load a single brush preset from a JSON file.
        
        Expected JSON format:
        {
            "name": "my_brush",
            "description": "Custom brush description",
            "tip_shape": "round",
            "pencil_hardness": 0.5,
            "pencil_sharpness": 0.7,
            "graphite_load": 0.8,
            "base_size": 8,
            "paper_type": "cold_press",
            "texture_strength": 0.5,
            "grain_scale": 1.0,
            "attack_ratio": 0.1,
            "release_ratio": 0.15,
            "sustain_noise": 0.05,
            "tremor_frequency": 20.0,
            "tremor_amplitude": 0.03,
            "velocity_influence": 0.5,
            "max_density": 1.0,
            "saturation_curve": 0.7,
            "layer_blending": 0.8
        }
        """
        if not os.path.exists(filepath):
            return None
            
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
        
        name = data.get("name", os.path.splitext(os.path.basename(filepath))[0])
        description = data.get("description", f"Custom brush: {name}")
        
        # Map strings to enums
        tip_map = {"round": TipShape.ROUND, "chisel": TipShape.CHISEL, "blunt": TipShape.BLUNT}
        paper_map = {"smooth": PaperType.SMOOTH, "cold_press": PaperType.COLD_PRESS, "rough": PaperType.ROUGH}
        
        config = AdaptiveBrushConfig(
            tip=PencilTipConfig(
                shape=tip_map.get(data.get("tip_shape", "round"), TipShape.ROUND),
                hardness=float(data.get("pencil_hardness", 0.5)),
                sharpness=float(data.get("pencil_sharpness", 0.7)),
                graphite_load=float(data.get("graphite_load", 0.8)),
                base_size=int(data.get("base_size", 8)),
            ),
            paper=PaperConfig(
                paper_type=paper_map.get(data.get("paper_type", "cold_press"), PaperType.COLD_PRESS),
                texture_strength=float(data.get("texture_strength", 0.5)),
                grain_scale=float(data.get("grain_scale", 1.0)),
            ),
            pressure=PressureConfig(
                attack_ratio=float(data.get("attack_ratio", 0.1)),
                release_ratio=float(data.get("release_ratio", 0.15)),
                sustain_noise=float(data.get("sustain_noise", 0.05)),
                tremor_frequency=float(data.get("tremor_frequency", 20.0)),
                tremor_amplitude=float(data.get("tremor_amplitude", 0.03)),
                velocity_influence=float(data.get("velocity_influence", 0.5)),
            ),
            accumulator=AccumulatorConfig(
                max_density=float(data.get("max_density", 1.0)),
                saturation_curve=float(data.get("saturation_curve", 0.7)),
                layer_blending=float(data.get("layer_blending", 0.8)),
            ),
        )
        
        return BrushPreset(name=name, description=description, config=config)
    
    @staticmethod
    def load_from_directory(dirpath: str) -> list:
        """
        Load all .json brush presets from a directory.
        
        Returns:
            List of loaded BrushPreset objects
        """
        loaded = []
        if not os.path.isdir(dirpath):
            return loaded
            
        for filename in sorted(os.listdir(dirpath)):
            if filename.endswith('.json'):
                filepath = os.path.join(dirpath, filename)
                preset = CustomBrushLoader.load_from_file(filepath)
                if preset is not None:
                    loaded.append(preset)
                    
        return loaded
    
    @staticmethod
    def load_and_register(dirpath: str) -> int:
        """
        Load all presets from a directory and register them.
        
        Returns:
            Number of presets loaded
        """
        presets = CustomBrushLoader.load_from_directory(dirpath)
        for preset in presets:
            BrushPresets.register(preset)
        return len(presets)
