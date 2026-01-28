# Counter-Strike Analytics

A comprehensive analytics framework for Counter-Strike 2 that provides detailed game analysis, economy tracking, player statistics, and machine learning-based round outcome prediction.

## Overview

This project parses CS2 demo files to extract detailed game data and provides statistical analysis, economy insights, and predictive modeling capabilities. It combines tick-by-tick player state tracking with advanced analytics to understand team performance, economic decisions, and round outcomes.

## Key Features

### Demo Parsing & Data Extraction
- **Full Game State Tracking**: Extracts player positions, health, armor, weapons, and money at configurable tick intervals
- **Comprehensive Event Capture**: Kills (with headshots, wallbangs, assists, trade kills), bomb events, grenade usage
- **Economy Data**: Automatic buy type classification (Pistol, Eco, Force, Full buy, Bonus)
- **Round Structure**: Precise round timing, freeze time, and result tracking

### Statistical Analysis
- **Player Statistics**: K/D ratios, headshot percentage, ADR, first kills, multikills (2k-5k)
- **Team Performance**: Side-specific win rates, pistol round analysis, eco round tracking
- **Key Round Identification**: Eco wins, force buy wins, momentum swings (3+ round streaks)
- **Economy Analysis**: Buy patterns, economic swings, money differential tracking, buy tendencies after wins/losses

### Spatial Analysis
- **Player Positioning**: Team spread calculation, centroid tracking, rotation detection
- **Map Support**: Pre-configured for 7 competitive maps (Dust2, Mirage, Inferno, Nuke, Vertigo, Ancient, Anubis)
- **Movement Analysis**: Player velocity and position-based metrics

### Machine Learning
- **Round Outcome Prediction**: Predict round winners based on economy and game state
- **Multiple Models**: Logistic Regression, Random Forest, Gradient Boosting (default)
- **Feature Engineering**: 27 features including economy metrics, score differential, momentum
- **Feature Importance**: Model interpretability with feature ranking
- **Dataset Management**: Build training datasets from multiple demos with train/test splitting

## Project Structure

```
counter-strike-analytics/
├── src/
│   ├── parsers/          # Demo file parsing and event extraction
│   ├── models/           # Pydantic data models
│   ├── analysis/         # Statistical analysis modules
│   ├── ml/               # Machine learning components
│   └── utils/            # Configuration and utilities
├── config/
│   ├── maps/             # Map-specific configurations
│   ├── economy.yaml      # Economy thresholds and buy types
│   └── weapons.yaml      # Weapon configurations
├── data/
│   ├── demos/            # Demo files (.dem)
│   └── parquet/          # Parquet dataset exports
└── examples/             # Example usage scripts
```

## Technologies

**Core Stack**:
- **demoparser2**: CS2 demo file parsing
- **pandas** & **numpy**: Data manipulation and analysis
- **pydantic**: Type-safe data models
- **pyarrow**: Efficient parquet storage

**Machine Learning**:
- **scikit-learn**: Classification models and feature engineering
- **xgboost**: Gradient boosting models
- **joblib**: Model serialization

**Visualization & Spatial**:
- **matplotlib**: Plotting and visualization
- **shapely**: Spatial data structures
- **PySide6**: GUI framework for interactive visualization

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Analysis

```python
from src.parsers.demo_parser import DemoParser
from src.analysis.match_analyzer import MatchAnalyzer

# Parse demo file
parser = DemoParser("data/demos/your_demo.dem")
match = parser.parse()

# Analyze match
analyzer = MatchAnalyzer(match)
summary = analyzer.get_match_summary()

print(f"Map: {match.map_name}")
print(f"Score: {summary['score']}")
print(f"Player Stats: {summary['player_stats']}")
```

### Economy Analysis

```python
from src.analysis.economy_analyzer import EconomyAnalyzer

# Analyze economy patterns
eco_analyzer = EconomyAnalyzer(match)
buy_patterns = eco_analyzer.get_buy_patterns()
swings = eco_analyzer.get_economy_swings()
```

### Machine Learning Prediction

```python
from src.ml.models.round_predictor import RoundPredictor
from src.ml.datasets import DatasetBuilder

# Build dataset from multiple demos
builder = DatasetBuilder()
dataset = builder.build_from_demos(["demo1.dem", "demo2.dem"])

# Train model
predictor = RoundPredictor(model_type="gradient_boosting")
predictor.train(dataset.X_train, dataset.y_train)

# Predict round outcome
prediction = predictor.predict(round_features)
print(f"Win probability: {prediction['win_probability']}")
```

See `examples/` directory for complete usage examples.

## Components

### Parsers
- **DemoParser**: Main parser for extracting game data from demo files
- **Event utilities**: Trade kill detection, ADR calculation, multikill counting

### Analysis
- **MatchAnalyzer**: Player and team statistics, key rounds, momentum analysis
- **EconomyAnalyzer**: Buy patterns, economic swings, money differential tracking

### Machine Learning
- **RoundPredictor**: ML models for round outcome prediction
- **RoundFeatureExtractor**: Feature engineering for ML training
- **DatasetBuilder**: Dataset creation from multiple demos with train/test splitting

### Data Models
Pydantic-based models for type safety:
- **Match**: Complete match data with teams, rounds, and scores
- **RoundState**: Round timing and results
- **PlayerState**: Player snapshot (position, health, inventory, money)
- **EconomyState**: Team economy and buy classification
- **Kill/BombEvent/GrenadeEvent**: Event models with detailed metadata

## Configuration

YAML-based configuration system:
- **Economy thresholds**: Buy type classification rules
- **Map configurations**: Map-specific boundaries and zones
- **Weapon data**: Categorization and pricing

## Data Output

- **Parquet files**: Efficient storage for large datasets in `data/parquet/`
- **In-memory models**: Pydantic models for real-time analysis
- **Model serialization**: Save/load trained ML models

## Future Enhancements

- Heat map generation and visualization
- Utility usage analysis (smokes, flashes, molotovs)
- Advanced spatial clustering and positioning analytics
- Interactive GUI for demo playback and analysis
- Team composition and role analysis
