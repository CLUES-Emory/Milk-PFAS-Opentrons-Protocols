from opentrons import protocol_api
from opentrons import types
from opentrons.protocol_api import COLUMN, ALL

# Software and robot version requirements: 8.2.0

metadata = {
    'protocolName': 'Step 2: Milk Agilent Plate Conditioning + Supernatant Transfer',
    'author': 'Aryan Patel + Catherine Mullins',
    'description': 'Adds 500uL of conditioning solvent twice, 150uL of supernatant for equilibration, and 1000uL supernatant to EMR plate'
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

    # 1000uL tip rack for conditioning solvent addition (Slot A3)
    tips_solvent = protocol.load_labware(
        "opentrons_flex_96_tiprack_1000ul", "A3",
        adapter="opentrons_flex_96_tiprack_adapter")

    # 1000uL tip rack for supernatant transfer (Slot B3)
    tips_sample = protocol.load_labware(
        "opentrons_flex_96_tiprack_1000ul", "B3",
        adapter="opentrons_flex_96_tiprack_adapter")

    # 50uL filter tip rack for NH4OH addition — filter tips prevent aerosol contamination (Slot C3)
    tips_NH4OH = protocol.load_labware(
        "opentrons_flex_96_filtertiprack_50ul", "C3",
        adapter="opentrons_flex_96_tiprack_adapter")

    # Abgene 2.2mL plate containing centrifuged sample supernatant from Step 1 (Slot C2)
    sample_plate = protocol.load_labware("abgene_96_wellplate_2200ul", "C2")

    # Reservoir containing conditioning solvent for SPE plate wash (Slot A2)
    solvent_reservoir = protocol.load_labware("nest_1_reservoir_195ml", "A2")

    # Reservoir containing 1% NH4OH in ACN for analyte elution (Slot A1)
    NH4OH_reservoir = protocol.load_labware("nest_1_reservoir_195ml", "A1")

    # Agilent EMR collection plate — receives conditioning solvent washes (Slot B1)
    solvent_destination_plate = protocol.load_labware("agilent_collectionplate_96wellplate_1000ul", "B1")

    # Agilent EMR collection plate — receives supernatant for analyte capture (Slot C1)
    sample_destination_plate  = protocol.load_labware("agilent_collectionplate_96wellplate_1000ul", "C1")

    # Abgene 2.2mL plate — final collection plate for NH4OH eluate (Slot D2)
    final_destination_plate = protocol.load_labware("abgene_96_wellplate_2200ul", "D2")

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
    # Adjust these values if liquid handling performance needs to be optimised.
    # -------------------------------------------------------------------------

    # Supernatant transfer parameters
    # Very slow rates minimise disturbance of the pellet/fat layer interface
    sample_asp_rate     = 20    # aspirate flow rate for supernatant (uL/sec)
    sample_disp_rate    = 20    # dispense flow rate for supernatant (uL/sec)
    sample_blowout_rate = 75    # blow-out flow rate for supernatant (uL/sec)
    sample_vol          = 1000  # total supernatant volume to transfer (uL)
                                # delivered in two 500uL passes
    equilibrate_vol     = 150   # volume used to equilibrate the EMR plate before capture (uL)

    # Conditioning solvent parameters
    solvent_asp_rate    = 92    # aspirate flow rate for conditioning solvent (uL/sec)
    solvent_disp_rate   = 92    # dispense flow rate for conditioning solvent (uL/sec)
    solvent_blowout_rate = 1000 # blow-out flow rate for conditioning solvent (uL/sec)
    solvent_volume      = 1000  # total conditioning solvent volume (uL)
                                # delivered in two 500uL washes

    # NH4OH parameters
    NH4OH_volume = 30           # volume of 1% NH4OH in ACN for elution (uL)

    # Target well — 'A1' addresses all 96 wells simultaneously with the 96-channel pipette
    well = 'A1'

    # -------------------------------------------------------------------------
    # PROCEDURE
    # -------------------------------------------------------------------------

    # Step 1: Condition the Agilent EMR plate with two 500uL solvent washes
    # Pre-wetting the sorbent bed ensures consistent analyte retention
    prewet(pipette, tips_solvent, solvent_volume, solvent_reservoir, well)

    solvent_addition_1(pipette, solvent_asp_rate, solvent_blowout_rate,
                       tips_solvent, solvent_volume, solvent_reservoir,
                       protocol, solvent_destination_plate, well)

    solvent_addition_2(pipette, solvent_asp_rate, solvent_blowout_rate,
                       tips_solvent, solvent_volume, solvent_reservoir,
                       protocol, solvent_destination_plate, well)

    pipette.drop_tip()

    # Technician must allow wash solvent to fully gravity-elute before loading sample
    protocol.pause('Allow wash solvent to gravity elute, then resume.')

    # Step 2: Load supernatant onto the EMR plate
    # First pass (150uL) equilibrates the plate; subsequent passes capture analytes
    supernatant_transfer_equilibrate(pipette, sample_asp_rate, sample_disp_rate,
                                     sample_blowout_rate, tips_sample, equilibrate_vol,
                                     sample_plate, protocol, solvent_destination_plate, well)

    supernatant_transfer(pipette, sample_asp_rate, sample_disp_rate, sample_blowout_rate,
                         tips_sample, sample_vol, sample_plate, protocol,
                         sample_destination_plate, well)

    supernatant_transfer(pipette, sample_asp_rate, sample_disp_rate, sample_blowout_rate,
                         tips_sample, sample_vol, sample_plate, protocol,
                         sample_destination_plate, well)

    pipette.drop_tip()

    # Technician applies positive pressure to push sample through the EMR plate,
    # then adds 1% NH4OH in ACN to reservoir A1 for the elution step
    protocol.pause('Allow sample to gravity elute, then apply positive pressure. Add 1% NH4OH in ACN to A1')

    # Step 3: Add 1% NH4OH in ACN to elute retained analytes into the final collection plate
    prewet_NH4OH(pipette, tips_NH4OH, NH4OH_volume, NH4OH_reservoir, well)

    NH4OH_addition(pipette, solvent_asp_rate, solvent_disp_rate, solvent_blowout_rate,
                   tips_NH4OH, NH4OH_volume, NH4OH_reservoir, protocol,
                   final_destination_plate, well)
    pipette.drop_tip()


# =============================================================================
# FUNCTIONS
# =============================================================================

def supernatant_transfer_equilibrate(pte, asp_rate, disp_rate, blow_rate, tips_sample,
                                     equilibrate_vol, samp_plate, protocol,
                                     solvent_dest_plate, well):
    """
    Transfers a small equilibration volume (150uL) of supernatant onto the
    conditioned Agilent EMR plate.

    The aspirate height is set to draw from just below the
    liquid surface to avoid disturbing the fat layer or pellet. An air gap
    prevents dripping during transit. A tip-wipe after dispense removes
    any hanging droplet from the tip exterior.

    Parameters
    ----------
    pte               : pipette object
    asp_rate          : aspirate flow rate (uL/sec)
    disp_rate         : dispense flow rate (uL/sec)
    blow_rate         : blow-out flow rate (uL/sec)
    tips_sample       : tip rack labware object
    equilibrate_vol   : volume of supernatant for equilibration (uL)
    samp_plate        : source labware (Abgene 2.2mL plate with supernatant)
    protocol          : protocol context
    solvent_dest_plate: destination labware (Agilent EMR plate for conditioning)
    well              : well address string (e.g. 'A1')
    """
    pte.flow_rate.aspirate = asp_rate  # uL/sec
    pte.flow_rate.dispense = disp_rate  # uL/sec
    pte.flow_rate.blow_out = blow_rate  # uL/sec

    # Delivers supernatant
    pte.pick_up_tip(tips_sample)

    # Aspirate from 28mm below the well top to draw from just below the liquid surface,
    # avoiding the fat layer (top) and pellet (bottom)
    pte.aspirate(equilibrate_vol, samp_plate[well].top(-28))
    pte.move_to(samp_plate[well].top(), speed=50)

    # Reduce aspirate rate before air gap to prevent pulling liquid back into the tip bore
    pte.flow_rate.aspirate = 15
    pte.air_gap(20)

    # Dispense 10mm below the well top; push_out=10 ensures complete delivery
    pte.dispense(equilibrate_vol + 20, solvent_dest_plate[well].top(-10), push_out=10)

    # Tip-wipe: dip then sweep laterally to shear off any hanging droplet
    pte.move_to(solvent_dest_plate[well].bottom(5))
    pte.move_to(solvent_dest_plate[well].top(-3))
    pte.move_to(solvent_dest_plate[well].top(-3).move(types.Point(y=4.2)))
    pte.move_to(solvent_dest_plate[well].top(-3).move(types.Point(y=-4.2)))


def supernatant_transfer(pte, asp_rate, disp_rate, blow_rate, tips_sample, samp_vol,
                         samp_plate, protocol, samp_dest_plate, well):
    """
    Transfers 500uL (half of samp_vol) of supernatant onto the Agilent EMR
    plate for analyte capture.

    The protocol pauses before each aspiration to allow the technician to apply
    positive pressure and reposition the EMR collection plate. The aspirate
    height (-29.5mm from top) must be validated experimentally to ensure the
    tip draws from the supernatant layer without disturbing the fat or pellet.

    This function is called twice in the procedure to transfer the full
    supernatant volume across two passes.

    Parameters
    ----------
    pte            : pipette object
    asp_rate       : aspirate flow rate (uL/sec)
    disp_rate      : dispense flow rate (uL/sec)
    blow_rate      : blow-out flow rate (uL/sec)
    tips_sample    : tip rack labware object (tips already loaded from equilibrate step)
    samp_vol       : total supernatant volume (uL); half is transferred per call
    samp_plate     : source labware (Abgene 2.2mL plate with supernatant)
    protocol       : protocol context (required for pause)
    samp_dest_plate: destination labware (Agilent EMR plate for analyte capture)
    well           : well address string (e.g. 'A1')
    """
    pte.flow_rate.aspirate = asp_rate  # uL/sec
    pte.flow_rate.dispense = disp_rate  # uL/sec
    pte.flow_rate.blow_out = blow_rate  # uL/sec

    # Delivers supernatant
    # Move to well top before pausing so the pipette is in position when the technician resumes
    pte.move_to(samp_plate[well].top())
    protocol.pause('Allow sample to gravity elute, apply positive pressure, change location of EMR plate then resume.')

    # Aspirate from 29.5mm below the well top
    pte.aspirate(samp_vol / 2, samp_plate[well].top(-29.5))
    pte.move_to(samp_plate[well].top(), speed=50)
    pte.air_gap(20)

    # Dispense 10mm below the well top; push_out=10 ensures complete delivery
    pte.dispense(samp_vol / 2 + 20, samp_dest_plate[well].top(-10), push_out=10)

    # Tip-wipe: dip then sweep laterally to shear off any hanging droplet
    pte.move_to(samp_dest_plate[well].bottom(5))
    pte.move_to(samp_dest_plate[well].top(-3))
    pte.move_to(samp_dest_plate[well].top(-3).move(types.Point(y=4.2)))
    pte.move_to(samp_dest_plate[well].top(-3).move(types.Point(y=-4.2)))


def prewet(pte, solvent_tip, solvent_vol, reservoir, well):
    """
    Pre-wets the conditioning solvent tips before delivery to the EMR plate.

    Pre-wetting coats the inner tip walls with solvent, which improves
    volumetric accuracy by reducing surface tension effects. Half the total
    solvent volume is aspirated and returned to the reservoir.

    Parameters
    ----------
    pte         : pipette object
    solvent_tip : tip rack labware object
    solvent_vol : total conditioning solvent volume (uL); half is used here
    reservoir   : source labware (NEST 195mL reservoir)
    well        : well address string (e.g. 'A1')
    """
    pte.pick_up_tip(solvent_tip)
    pte.flow_rate.aspirate = 92
    pte.flow_rate.dispense = 92

    # Aspirate 5mm above reservoir bottom to avoid drawing in sediment
    pte.aspirate(solvent_vol / 2, reservoir[well].bottom(5))
    pte.move_to(reservoir[well].top(), speed=50)

    # Reduce aspirate rate before air gap to prevent pulling liquid back
    pte.flow_rate.aspirate = 15
    pte.air_gap(20)

    # Dispense back into reservoir to complete pre-wet; push_out clears the tip bore
    pte.dispense(solvent_vol / 2 + 20, reservoir[well].top(-2), push_out=10)
    pte.blow_out()
    pte.blow_out()


def solvent_addition_1(pte, solvent_asp, solvent_blow, solvent_tip, solvent_vol,
                       reservoir, protocol, solvent_dest_plate, well):
    """
    Delivers the first 500uL of conditioning solvent (half of solvent_vol)
    to the Agilent EMR plate.

    A slow dispense rate (30uL/sec) is used to prevent solvent from
    channelling through the sorbent bed. A tip-wipe after dispense removes
    any hanging droplet from the tip exterior.

    Parameters
    ----------
    pte               : pipette object
    solvent_asp       : aspirate flow rate (uL/sec)
    solvent_blow      : blow-out flow rate (uL/sec)
    solvent_tip       : tip rack labware object (tips already loaded from prewet step)
    solvent_vol       : total conditioning solvent volume (uL); half is delivered here
    reservoir         : source labware (NEST 195mL reservoir)
    protocol          : protocol context
    solvent_dest_plate: destination labware (Agilent EMR collection plate)
    well              : well address string (e.g. 'A1')
    """
    pte.flow_rate.aspirate = solvent_asp
    pte.flow_rate.dispense = 30   # slow dispense to prevent channelling through the sorbent bed
    pte.flow_rate.blow_out = solvent_blow

    # Delivers half of solvent
    # solvent_vol is divided in half here because it requires 2 deliveries to stay within tip capacity
    pte.aspirate(solvent_vol / 2, reservoir[well].bottom(1))
    pte.move_to(reservoir[well].top(), speed=50)

    # Reduce aspirate rate before air gap to prevent pulling liquid back
    pte.flow_rate.aspirate = 15
    pte.air_gap(20)

    # Dispense 10mm below the well top; push_out=10 ensures complete delivery
    pte.dispense(solvent_vol / 2 + 20, solvent_dest_plate[well].top(-10), push_out=10)

    # Tip-wipe: dip then sweep laterally to shear off any hanging droplet
    pte.move_to(solvent_dest_plate[well].bottom(5))
    pte.move_to(solvent_dest_plate[well].top(-1))
    pte.move_to(solvent_dest_plate[well].top(-1).move(types.Point(y=4.2)))
    pte.move_to(solvent_dest_plate[well].top(-1).move(types.Point(y=-4.2)))


def solvent_addition_2(pte, solvent_asp, solvent_blow, solvent_tip, solvent_vol,
                       reservoir, protocol, solvent_dest_plate, well):
    """
    Delivers the second 500uL of conditioning solvent (half of solvent_vol)
    to the Agilent EMR plate.

    The protocol pauses before aspiration to allow the first wash to fully
    gravity-elute through the sorbent bed before the second wash is applied.

    Parameters
    ----------
    pte               : pipette object
    solvent_asp       : aspirate flow rate (uL/sec)
    solvent_blow      : blow-out flow rate (uL/sec)
    solvent_tip       : tip rack labware object (tips already loaded from prewet step)
    solvent_vol       : total conditioning solvent volume (uL); half is delivered here
    reservoir         : source labware (NEST 195mL reservoir)
    protocol          : protocol context (required for pause)
    solvent_dest_plate: destination labware (Agilent EMR collection plate)
    well              : well address string (e.g. 'A1')
    """
    pte.flow_rate.aspirate = solvent_asp
    pte.flow_rate.dispense = 30   # slow dispense to prevent channelling through the sorbent bed
    pte.flow_rate.blow_out = solvent_blow

    # Delivers half of solvent
    # Move to reservoir top before pausing so the pipette is in position when the technician resumes
    pte.move_to(reservoir[well].top())

    # Pause to allow first wash to fully gravity-elute before applying second wash
    protocol.pause('Allow wash solvent to gravity elute, then resume.')

    # solvent_vol is divided in half here because it requires 2 deliveries to stay within tip capacity
    pte.aspirate(solvent_vol / 2, reservoir[well].bottom(1))
    pte.move_to(reservoir[well].top(), speed=50)

    # Reduce aspirate rate before air gap to prevent pulling liquid back
    pte.flow_rate.aspirate = 15
    pte.air_gap(20)

    # Dispense 10mm below the well top; push_out=10 ensures complete delivery
    pte.dispense(solvent_vol / 2 + 20, solvent_dest_plate[well].top(-10), push_out=10)

    # Tip-wipe: dip then sweep laterally to shear off any hanging droplet
    pte.move_to(solvent_dest_plate[well].bottom(5))
    pte.move_to(solvent_dest_plate[well].top(-1))
    pte.move_to(solvent_dest_plate[well].top(-1).move(types.Point(y=4.2)))
    pte.move_to(solvent_dest_plate[well].top(-1).move(types.Point(y=-4.2)))


def prewet_NH4OH(pte, NH4OH_tip, NH4OH_vol, NH4OH_reservoir, well):
    """
    Pre-wets the filter tips with 1% NH4OH in ACN before elution.

    Pre-wetting ensures accurate delivery of this small volume (30uL) by
    coating the tip walls before the actual elution step.

    Parameters
    ----------
    pte            : pipette object
    NH4OH_tip      : tip rack labware object (50uL filter tips)
    NH4OH_vol      : volume of NH4OH solution (uL)
    NH4OH_reservoir: source labware (NEST 195mL reservoir)
    well           : well address string (e.g. 'A1')
    """
    pte.pick_up_tip(NH4OH_tip)
    pte.flow_rate.aspirate = 92
    pte.flow_rate.dispense = 92

    # Aspirate 2mm above the reservoir bottom
    pte.aspirate(NH4OH_vol, NH4OH_reservoir[well].bottom(2))
    pte.move_to(NH4OH_reservoir[well].top(), speed=50)

    # Reduce aspirate rate before air gap to prevent pulling liquid back
    pte.flow_rate.aspirate = 15
    pte.air_gap(10)

    # Dispense back into reservoir to complete pre-wet; push_out clears the tip bore
    pte.dispense(NH4OH_vol + 10, NH4OH_reservoir[well].top(-2), push_out=10)
    pte.blow_out()
    pte.blow_out()


def NH4OH_addition(pte, solvent_asp, solvent_disp, solvent_blow, NH4OH_tip, NH4OH_vol,
                   NH4OH_reservoir, protocol, final_dest_plate, well):
    """
    Delivers 30uL of 1% NH4OH in ACN to the final Abgene collection plate.

    A tip-wipe after dispense removes any hanging droplet from the tip exterior.

    Parameters
    ----------
    pte             : pipette object
    solvent_asp     : aspirate flow rate (uL/sec)
    solvent_disp    : dispense flow rate (uL/sec)
    solvent_blow    : blow-out flow rate (uL/sec)
    NH4OH_tip       : tip rack labware object (tips already loaded from prewet_NH4OH step)
    NH4OH_vol       : volume of 1% NH4OH in ACN to deliver (uL)
    NH4OH_reservoir : source labware (NEST 195mL reservoir)
    protocol        : protocol context
    final_dest_plate: destination labware (Abgene 2.2mL final collection plate)
    well            : well address string (e.g. 'A1')
    """
    pte.flow_rate.aspirate = solvent_asp
    pte.flow_rate.dispense = solvent_disp
    pte.flow_rate.blow_out = solvent_blow

    # Delivers NH4OH
    # Aspirate 2mm above the reservoir bottom
    pte.aspirate(NH4OH_vol, NH4OH_reservoir[well].bottom(2))
    pte.move_to(NH4OH_reservoir[well].top(), speed=50)

    # Reduce aspirate rate before air gap to prevent pulling liquid back
    pte.flow_rate.aspirate = 15
    pte.air_gap(10)

    # Dispense 10mm below the well top; push_out=10 ensures complete delivery
    pte.dispense(NH4OH_vol + 10, final_dest_plate[well].top(-10), push_out=10)

    # Tip-wipe: dip then sweep laterally to shear off any hanging droplet
    pte.move_to(final_dest_plate[well].bottom(5))
    pte.move_to(final_dest_plate[well].top(-1))
    pte.move_to(final_dest_plate[well].top(-1).move(types.Point(y=4.2)))
    pte.move_to(final_dest_plate[well].top(-1).move(types.Point(y=-4.2)))
