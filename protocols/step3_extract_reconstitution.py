from opentrons import protocol_api
from opentrons import types
from opentrons.protocol_api import COLUMN, ALL

# Software and robot version requirements: 8.2.0

metadata = {
    'protocolName': 'Step 3: Milk Extract Reconstitution',
    'author': 'Aryan Patel + Catherine Mullins',
    'description': 'Adds 50ul of 20:80 Water/Methanol to sample plate.'
}

requirements = {"robotType": "Flex", "apiLevel": "2.20"}


def run(protocol: protocol_api.ProtocolContext):

    # -------------------------------------------------------------------------
    # SETUP
    # -------------------------------------------------------------------------

    # Turn on deck lights
    protocol.set_rail_lights(True)

    # Define waste chute location for tip disposal
    chute = protocol.load_waste_chute()

    # -------------------------------------------------------------------------
    # LABWARE
    # -------------------------------------------------------------------------

    # 200uL filter tip rack for reconstitution solvent addition (Slot C3)
    # Filter tips are used here to prevent aerosol contamination of the dried extract
    tips_solvent = protocol.load_labware(
        "opentrons_flex_96_filtertiprack_200ul", "C3",
        adapter="opentrons_flex_96_tiprack_adapter")

    # Reservoir containing 20:80 water/methanol reconstitution solvent (Slot B1)
    solvent_reservoir  = protocol.load_labware("nest_1_reservoir_195ml",    "B1")

    # Abgene 2.2mL deep well plate containing the dried-down extract from Step 2 (Slot C2)
    destination_plate  = protocol.load_labware("abgene_96_wellplate_2200ul", "C2")

    # -------------------------------------------------------------------------
    # PIPETTE
    # -------------------------------------------------------------------------

    # 96-channel 1000uL pipette — operates on all 96 wells simultaneously
    pipette = protocol.load_instrument(
        instrument_name="flex_96channel_1000"
    )

    # -------------------------------------------------------------------------
    # PARAMETERS
    # All flow rates are in uL/sec. All volumes are in uL.
    # Please do not change these values unless you are confident in the
    # modification and plan to validate the change with a test run.
    # -------------------------------------------------------------------------

    solvent_asp_rate     = 92   # aspirate flow rate for reconstitution solvent (uL/sec)
    solvent_disp_rate    = 92   # dispense flow rate for reconstitution solvent (uL/sec)
    solvent_blowout_rate = 1000 # blow-out flow rate for reconstitution solvent (uL/sec)
    solvent_volume       = 50   # volume of reconstitution solvent to add per well (uL)

    # Target well — 'A1' addresses all 96 wells simultaneously with the 96-channel pipette
    well = 'A1'

    # -------------------------------------------------------------------------
    # PROCEDURE
    # -------------------------------------------------------------------------

    # Add 50uL of 20:80 water/methanol to reconstitute the dried-down extract
    prewet(pipette, tips_solvent, solvent_volume, solvent_reservoir, well)
    solvent_addition(pipette, solvent_asp_rate, solvent_disp_rate, solvent_blowout_rate,
                     solvent_volume, solvent_reservoir, protocol, destination_plate, well)
    pipette.drop_tip()


# =============================================================================
# FUNCTIONS
# =============================================================================

def prewet(pte, solvent_tip, solvent_vol, reservoir, well):
    """
    Pre-wets the filter tips with reconstitution solvent before delivery.

    Pre-wetting coats the inner tip walls, which is especially important for
    small volumes (50uL) where surface tension effects can significantly impact
    volumetric accuracy. The full solvent volume is aspirated and returned to
    the reservoir to complete the pre-wet cycle.

    Parameters
    ----------
    pte         : pipette object
    solvent_tip : tip rack labware object (200uL filter tips)
    solvent_vol : volume of reconstitution solvent (uL)
    reservoir   : source labware (NEST 195mL reservoir)
    well        : well address string (e.g. 'A1')
    """
    pte.pick_up_tip(solvent_tip)
    pte.flow_rate.aspirate = 92
    pte.flow_rate.dispense = 92

    # Aspirate 2mm above the reservoir bottom to avoid drawing in air or sediment
    pte.aspirate(solvent_vol, reservoir[well].bottom(2))
    pte.move_to(reservoir[well].top(), speed=50)

    # Reduce aspirate rate before air gap to prevent pulling liquid back into the tip bore
    pte.flow_rate.aspirate = 15
    pte.air_gap(20)

    # Dispense back into reservoir to complete pre-wet; push_out clears the tip bore
    pte.dispense(solvent_vol + 20, reservoir[well].top(-2), push_out=10)
    pte.blow_out()
    pte.blow_out()


def solvent_addition(pte, solvent_asp, solvent_disp, solvent_blow, solvent_vol,
                     reservoir, protocol, dest_plate, well):
    """
    Delivers 50uL of 20:80 water/methanol reconstitution solvent to each well
    of the dried-down Abgene plate.

    Solvent is dispensed from 10mm below the well top to direct the liquid
    toward the dried extract at the well bottom. An air gap prevents dripping
    during transit. A tip-wipe after dispense removes any hanging droplet from
    the tip exterior.

    Parameters
    ----------
    pte        : pipette object
    solvent_asp: aspirate flow rate (uL/sec)
    solvent_disp: dispense flow rate (uL/sec)
    solvent_blow: blow-out flow rate (uL/sec)
    solvent_vol: volume of reconstitution solvent to deliver (uL)
    reservoir  : source labware (NEST 195mL reservoir)
    protocol   : protocol context
    dest_plate : destination labware (Abgene 2.2mL plate with dried extract)
    well       : well address string (e.g. 'A1')
    """
    pte.flow_rate.aspirate = solvent_asp
    pte.flow_rate.dispense = solvent_disp
    pte.flow_rate.blow_out = solvent_blow

    # Aspirate 2mm above the reservoir bottom to avoid drawing in air or sediment
    pte.aspirate(solvent_vol, reservoir[well].bottom(2))
    pte.move_to(reservoir[well].top(), speed=50)

    # Reduce aspirate rate before air gap to prevent pulling liquid back into the tip bore
    pte.flow_rate.aspirate = 15
    pte.air_gap(20)

    # Dispense 10mm below the well top to direct solvent toward the dried extract;
    # push_out=10 ensures complete delivery of the small volume
    pte.dispense(solvent_vol + 20, dest_plate[well].top(-10), push_out=10)

    # Tip-wipe: dip then sweep laterally to shear off any hanging droplet
    pte.move_to(dest_plate[well].bottom(5))
    pte.move_to(dest_plate[well].top(-1))
    pte.move_to(dest_plate[well].top(-1).move(types.Point(y=4.2)))
    pte.move_to(dest_plate[well].top(-1).move(types.Point(y=-4.2)))
