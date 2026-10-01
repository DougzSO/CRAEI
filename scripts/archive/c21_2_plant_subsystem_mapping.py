"""COMANDO C21-2 PARTE 2: Plant → ONS subsystem mapping.

Creates plant_id → subsystem {N, NE, S, SE} mapping for Brazilian hydroelectric plants.
"""

import sys

sys.path.insert(0, 'src')

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from craei.config import load_paths


def create_plant_subsystem_mapping():
    """Create plant → ONS subsystem mapping."""
    paths = load_paths()
    processed_dir = Path(paths['processed_dir'])

    # Load plants
    plants_path = processed_dir / 'plants.parquet'
    plants = pd.read_parquet(plants_path)

    # Filter to Brazil only and hydro plants
    brazil_hydro = plants[
        (plants['country'] == 'BRA') &
        (plants['tech_class'] == 'hydro')
    ].copy()

    logger.info(f"Processing {len(brazil_hydro)} Brazil hydro plants")

    # Geographic inference - use latitude to map to ONS subsystem
    # ONS subsystems by approximate latitude ranges
    def infer_subsystem_from_lat(lat):
        if lat >= -5:  # North (roughly 0 to -5)
            return 'N'
        elif lat >= -16:  # Northeast (-5 to -16)
            return 'NE'
        elif lat >= -27:  # Southeast (-16 to -27)
            return 'SE'
        else:  # South (< -27)
            return 'S'

    brazil_hydro['subsystem'] = brazil_hydro['lat'].apply(infer_subsystem_from_lat)

    # Create the output dataframe with required fields
    output_df = pd.DataFrame({
        'plant_id': brazil_hydro['plant_uid'],
        'plant_name': brazil_hydro['plant_name'],
        'latitude': brazil_hydro['lat'],
        'longitude': brazil_hydro['lon'],
        'subsystem': brazil_hydro['subsystem'],
        'capacity_mw': brazil_hydro['capacity_mw']
    })

    # Add metadata columns
    output_df['mapping_method'] = 'geographic_latitude_inference'
    output_df['mapping_source'] = 'simplified_ons_geographic_bounds'
    output_df['mapping_confidence'] = 'medium'

    # Validation audit
    n_total = len(output_df)
    n_by_subsystem = output_df['subsystem'].value_counts().to_dict()

    logger.info("\nPlant-Subsystem Mapping Audit:")
    logger.info(f"  Total plants: {n_total}")
    logger.info(f"  By subsystem: {n_by_subsystem}")

    # Check for duplicates
    n_duplicates = output_df['plant_id'].duplicated().sum()
    logger.info(f"  Duplicates: {n_duplicates}")

    # Coordinate validation
    invalid_coords = (
        (output_df['latitude'].isna()) |
        (output_df['longitude'].isna()) |
        (output_df['latitude'].abs() > 90) |
        (output_df['longitude'].abs() > 180)
    ).sum()
    logger.info(f"  Invalid coordinates: {invalid_coords}")

    # Save output
    output_path = processed_dir / 'plant_subsystem_mapping.parquet'
    output_df.to_parquet(output_path)
    logger.info(f"  Saved to: {output_path}")

    return output_df

if __name__ == '__main__':
    mapping_df = create_plant_subsystem_mapping()
    print(f"\nCreated mapping for {len(mapping_df)} plants")
    print(mapping_df[['plant_name', 'subsystem', 'mapping_confidence']].head(10))
