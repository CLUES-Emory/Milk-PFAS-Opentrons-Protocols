# Automated PFAS Extraction from Human Milk

Opentrons Flex protocols for high-throughput PFAS extraction from human milk using 96-well Enhanced Matrix Removal (EMR) cleanup. These protocols automate the sample preparation workflow described in:

> **A Scalable, High-Throughput Method for PFAS Quantitation in Human Milk**
> [Author list and journal citation to be added upon publication]

## Overview

This repository contains three Python protocols for the Opentrons Flex liquid handler that together automate the extraction of 23 PFAS from 300 µL of human milk. The workflow processes a full 96-well plate (72 samples + 24 QA/QC materials) in approximately 4 hours of preparation time, with minimal manual intervention.

The protocols use the Opentrons Flex 96-channel 1000 µL pipette, which operates on all 96 wells simultaneously.

## Workflow

| Step | Protocol | Description | Hands-on time |
|------|----------|-------------|---------------|
| 1 | `step1_sample_aliquoting_and_solvent_addition.py` | Aliquot 300 µL milk + add 1200 µL extraction solvent | ~5 min |
| 2 | — | **Off-robot:** Vortex 10 min, centrifuge 15 min at 3,940 × g, 4°C | ~30 min |
| 3 | `step2_conditioning_and_supernatant_loading.py` | EMR plate conditioning, supernatant loading, NH₄OH addition | ~10 min |
| 4 | — | **Off-robot:** Positive pressure elution, evaporative dry-down (N₂, 50°C, ~2 hr) | ~2 hr |
| 5 | `step3_extract_reconstitution.py` | Reconstitute dried extract in 50 µL 20:80 water/methanol | ~5 min |
| 6 | — | **Off-robot:** Vortex 5 min, sonicate 5 min, centrifuge 3 min | ~15 min |

After Step 6, samples are ready for LC-HRMS analysis.

## Protocol Details

### Step 1: Sample Aliquoting and Extraction Solvent Addition

Transfers 300 µL of human milk from a temperature-controlled Matrix tube rack (4°C) into an Abgene 2.2 mL deep-well plate, then adds 1200 µL of extraction solvent (acetonitrile with 1% formic acid and isotope-labeled internal standards) in two 600 µL deliveries.

**Key features:**
- Slow aspiration (30 µL/sec) to avoid disturbing sample particulates
- 2-second post-aspirate delay for liquid column stabilization
- Air gaps (20 µL) to prevent dripping during transit
- Pre-wetting of extraction solvent tips for volumetric accuracy
- Tip-wipe after dispense to remove hanging droplets

**Deck layout:**

| Slot | Labware |
|------|---------|
| A1 | 1000 µL tip rack (sample transfer) |
| B3 | 1000 µL tip rack (extraction solvent) |
| C1 | NEST 195 mL reservoir (extraction solvent) |
| C2 | Abgene 2.2 mL deep-well plate (destination) |
| D1 | Temperature module + Matrix tube rack (samples, 4°C) |

### Step 2: EMR Plate Conditioning and Supernatant Loading

Conditions the Agilent EMR-PFAS Food II plate with two 500 µL solvent washes, loads supernatant in three passes (150 µL equilibration + 2 × 500 µL capture), and adds 30 µL of 1% NH₄OH in acetonitrile to the final collection plate.

**Key features:**
- Slow dispense rate (30 µL/sec) during conditioning to prevent sorbent channeling
- Very slow supernatant aspiration (20 µL/sec) to avoid disturbing the pellet/fat layer
- Aspiration from below the liquid surface to avoid fat layer contamination
- 150 µL equilibration pass to passivate active sites before full sample loading
- Filter tips (50 µL) for NH₄OH addition to prevent aerosol contamination
- Multiple pause points for gravity elution and positive pressure steps

**Deck layout:**

| Slot | Labware |
|------|---------|
| A1 | NEST 195 mL reservoir (1% NH₄OH in ACN) |
| A2 | NEST 195 mL reservoir (conditioning solvent) |
| A3 | 1000 µL tip rack (conditioning solvent) |
| B1 | Agilent EMR collection plate (conditioning waste) |
| B3 | 1000 µL tip rack (supernatant transfer) |
| C1 | Agilent EMR collection plate (sample eluate) |
| C2 | Abgene 2.2 mL plate (centrifuged supernatant from Step 1) |
| C3 | 50 µL filter tip rack (NH₄OH) |
| D2 | Abgene 2.2 mL plate (final collection) |

**Manual interventions (protocol pauses):**
1. Allow conditioning wash solvent to gravity-elute before second wash
2. Allow second wash to gravity-elute before sample loading
3. After sample loading: gravity-elute, apply positive pressure, then add NH₄OH to reservoir A1

### Step 3: Extract Reconstitution

Adds 50 µL of 20:80 water/methanol reconstitution solvent to the dried-down extract in the Abgene plate.

**Key features:**
- Pre-wetting of filter tips for accurate delivery of small volumes
- Reduced aspirate rate (15 µL/sec) before air gap to prevent pulling liquid back into the tip bore
- Tip-wipe after dispense

**Deck layout:**

| Slot | Labware |
|------|---------|
| B1 | NEST 195 mL reservoir (20:80 water/methanol) |
| C2 | Abgene 2.2 mL plate (dried extract from Step 2) |
| C3 | 200 µL filter tip rack |

## Requirements

- **Robot:** Opentrons Flex
- **Software:** Opentrons App 8.2.0 or later
- **API Level:** 2.20
- **Pipette:** Flex 96-channel 1000 µL
- **Modules:** Temperature Module Gen2 (Step 1 only)

### Labware

| Item | Part Number | Used In |
|------|-------------|---------|
| Opentrons Flex 96 tip rack, 1000 µL | — | Steps 1, 2 |
| Opentrons Flex 96 filter tip rack, 200 µL | — | Step 3 |
| Opentrons Flex 96 filter tip rack, 50 µL | — | Step 2 |
| Matrix 96-well tube rack, 500 µL | — | Step 1 |
| Abgene 96 deep-well plate, 2.2 mL | — | Steps 1, 2, 3 |
| Agilent EMR-PFAS Food II 96-well plate | — | Step 2 |
| Agilent EMR collection plate, 1 mL | — | Step 2 |
| NEST 1-well reservoir, 195 mL | — | Steps 1, 2, 3 |

### Reagents

| Reagent | Purpose |
|---------|---------|
| Acetonitrile with 1% formic acid + isotope-labeled PFAS IS | Extraction solvent (Step 1) |
| 1:1 acetonitrile/methanol with 1% formic acid | EMR conditioning solvent (Step 2) |
| 1% NH₄OH in acetonitrile | Keeper solvent to prevent short-chain PFCA loss during dry-down (Step 2) |
| 20:80 water/methanol | Reconstitution solvent (Step 3) |

## Custom Labware

The Abgene 2.2 mL plate, Matrix tube rack, and Agilent EMR plates require custom labware definitions that are not included in the default Opentrons labware library. Custom definitions must be uploaded to the Opentrons App before running these protocols. Contact the authors or generate definitions using the [Opentrons Labware Creator](https://labware.opentrons.com/create/).

## Usage

1. Upload the protocol files and any custom labware definitions to the Opentrons App.
2. Calibrate the Flex 96-channel pipette and verify deck layout for each step.
3. Run protocols in order (Step 1 → Step 2 → Step 3), performing the off-robot steps (vortexing, centrifugation, evaporation) between each protocol.
4. Follow on-screen pause prompts for manual interventions (adding reagents, gravity elution, positive pressure).

## Adjustable Parameters

Flow rates and volumes are defined as named variables at the top of each protocol and can be modified if needed. Key parameters:

| Parameter | Default | Protocol |
|-----------|---------|----------|
| Sample volume | 300 µL | Step 1 |
| Extraction solvent volume | 1200 µL | Step 1 |
| Conditioning solvent volume | 2 × 500 µL | Step 2 |
| Equilibration volume | 150 µL | Step 2 |
| Supernatant loading volume | 2 × 500 µL | Step 2 |
| NH₄OH volume | 30 µL | Step 2 |
| Reconstitution volume | 50 µL | Step 3 |

## Citation

If you use these protocols, please cite:

> [Citation to be added upon publication]

## Authors

Aryan Patel and Catherine Mullins
Comprehensive Laboratory for Untargeted Exposome Science (CLUES)
Gangarosa Department of Environmental Health
Rollins School of Public Health, Emory University

## License

[To be determined]
