from opentrons import protocol_api
from opentrons import types
from opentrons.protocol_api import COLUMN, ALL

# Software and robot version requirements: 8.2.0

metadata = {
    'protocolName': 'Step 1: Sample Aliquoting + Extraction Solvent Addition',
    'author': 'Aryan Patel + Catherine Mullins',
    'description': 'Adds 300uL of sample and 1200uL extraction solvent to Abgene 2.2mL well plate'
}

requirements = {"robotType": "Flex", "apiLevel": "2.20"}


def run(protocol: protocol_api.ProtocolContext):

    # -------------------------------------------------------------------------
    # SETUP
    # -------------------------------------------------------------------------

    # Turn on deck lights for visibility during run
    protocol.set_rail_lights(True)

    # Define waste chute location for tip disposal
    chute = protocol.load_waste_chute()

    # -------------------------------------------------------------------------
    # LABWARE
    # -------------------------------------------------------------------------

    # 1000uL tip rack for sample aspiration (Slot A1)
    tips_sample = protocol.load_labware(
        "opentrons_flex_96_tiprack_1000ul", "A1",
        adapter="opentrons_flex_96_tiprack_adapter")

    # 1000uL tip rack for extraction solvent addition (Slot B3)
    tips_ES = protocol.load_labware(
        "opentrons_flex_96_tiprack_1000ul", "B3",
        adapter="opentrons_flex_96_tiprack_adapter")

    # Temperature module set to 4°C to keep samples cold during aliquoting (Slot D1)
    temp_mod = protocol.load_module('temperature module gen2', "D1")
    temp_mod.set_temperature(4)
    sample_plate = temp_mod.load_labware("matrix96well_96_tuberack_500ul")

    # Reservoir containing extraction solvent (Slot C1)
    ES_reservoir      = protocol.load_labware("nest_1_reservoir_195ml",    "C1")

    # Abgene 2.2mL deep well plate — receives sample and extraction solvent (Slot C2)
    destination_plate = protocol.load_labware("abgene_96_wellplate_2200ul", "C2")

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

    # Sample transfer parameters
    # Slow aspirate/dispense rates prevent disturbing the sample and reduce air bubbles
    sample_asp_rate     = 30    # aspirate flow rate for sample (uL/sec)
    sample_disp_rate    = 30    # dispense flow rate for sample (uL/sec)
    sample_blowout_rate = 75    # blow-out flow rate for sample (uL/sec)
    sample_vol          = 300   # volume of sample to transfer (uL)

    # Extraction solvent (ES) parameters
    # Higher flow rates are appropriate for the less viscous extraction solvent
    ES_asp_rate     = 716       # aspirate flow rate for extraction solvent (uL/sec)
    ES_disp_rate    = 716       # dispense flow rate for extraction solvent (uL/sec)
    ES_blowout_rate = 1000      # blow-out flow rate for extraction solvent (uL/sec)
    ES_volume       = 1200      # total volume of extraction solvent to add (uL)
                                # delivered in two 600uL additions to stay within tip capacity

    # Target well — 'A1' addresses all 96 wells simultaneously with the 96-channel pipette
    well = 'A1'

    # -------------------------------------------------------------------------
    # PROCEDURE
    # -------------------------------------------------------------------------

    # Step 1: Aliquot sample from temperature-controlled Matrix rack into destination plate
    sample_aliquot(pipette, sample_asp_rate, sample_disp_rate, sample_blowout_rate,
                   tips_sample, sample_vol, sample_plate, protocol, destination_plate, well)

    # Step 2: Add extraction solvent in two 600uL deliveries
    # Technician must add extraction solvent to the reservoir before resuming
    protocol.pause('Add Extraction Solvent, then resume.')
    prewet(pipette, ES_asp_rate, ES_disp_rate, ES_blowout_rate,
           tips_ES, ES_volume, ES_reservoir, well)
    ES_addition_1(pipette, ES_asp_rate, ES_disp_rate, ES_blowout_rate,
                  tips_ES, ES_volume, ES_reservoir, protocol, destination_plate, well)
    ES_addition_2(pipette, ES_asp_rate, ES_disp_rate, ES_blowout_rate,
                  tips_ES, ES_volume, ES_reservoir, protocol, destination_plate, well)
    pipette.drop_tip()


# =============================================================================
# FUNCTIONS
# =============================================================================

def sample_aliquot(pte, asp_rate, disp_rate, blow_rate, tip, samp_vol,
                   samp_plate, protocol, dest_plate, well):
    """
    Aspirates sample from the temperature-controlled Matrix tube rack and
    dispenses it into the Abgene destination plate.

    Slow flow rates are used to avoid disturbing particulates in the sample.
    A 2-second delay after aspiration allows the liquid column to stabilise
    before the pipette moves. An air gap of 20uL prevents dripping during
    transit. Double blow-out ensures complete liquid evacuation from the tip.

    Parameters
    ----------
    pte        : pipette object
    asp_rate   : aspirate flow rate (uL/sec)
    disp_rate  : dispense flow rate (uL/sec)
    blow_rate  : blow-out flow rate (uL/sec)
    tip        : tip rack labware object
    samp_vol   : volume of sample to transfer (uL)
    samp_plate : source labware (Matrix tube rack on temperature module)
    protocol   : protocol context (required for delay commands)
    dest_plate : destination labware (Abgene 2.2mL plate)
    well       : well address string (e.g. 'A1')
    """
    pte.flow_rate.aspirate = asp_rate  # uL/sec
    pte.flow_rate.dispense = disp_rate  # uL/sec
    pte.flow_rate.blow_out = blow_rate  # uL/sec

    pte.pick_up_tip(tip)

    # Aspirate 2mm above the tube bottom to avoid drawing up any pellet material
    pte.aspirate(samp_vol, samp_plate[well].bottom(2))

    # Wait 2 seconds for the liquid column to stabilise before moving
    protocol.delay(2)

    # Rise slowly (5mm/sec) to avoid dislodging liquid from the tip
    pte.move_to(samp_plate[well].top(), speed=5)

    # Air gap of 20uL seals the tip to prevent dripping during transit
    pte.air_gap(20)

    # Dispense 5mm above the plate bottom; push_out=10 ensures full delivery
    pte.dispense(samp_vol + 20, dest_plate[well].bottom(5), push_out=10)

    # Wait 1 second then double blow-out to ensure complete liquid transfer
    protocol.delay(1)
    pte.blow_out()
    pte.blow_out()
    pte.drop_tip()


def prewet(pte, ES_asp, ES_disp, ES_blow, ES_tip, ES_vol, reservoir, well):
    """
    Pre-wets the extraction solvent tips before delivery to the sample plate.

    Pre-wetting coats the inner tip walls with solvent, which improves
    volumetric accuracy on subsequent aspirations by reducing surface tension
    effects. Half the total ES volume is aspirated and returned to the
    reservoir to complete the pre-wet cycle.

    Parameters
    ----------
    pte       : pipette object
    ES_asp    : aspirate flow rate (uL/sec)
    ES_disp   : dispense flow rate (uL/sec)
    ES_blow   : blow-out flow rate (uL/sec)
    ES_tip    : tip rack labware object
    ES_vol    : total extraction solvent volume (uL); half is used here
    reservoir : source labware (NEST 195mL reservoir)
    well      : well address string (e.g. 'A1')
    """
    pte.pick_up_tip(ES_tip)
    pte.flow_rate.aspirate = ES_asp
    pte.flow_rate.dispense = ES_disp
    pte.flow_rate.blow_out = ES_blow

    # Aspirate half the ES volume 1mm above the reservoir bottom
    pte.aspirate(ES_vol / 2, reservoir[well].bottom(1))
    pte.move_to(reservoir[well].top(), speed=50)

    # Air gap of 20uL prevents dripping while moving
    pte.air_gap(20)

    # Dispense back into the reservoir to complete the pre-wet; push_out clears the tip bore
    pte.dispense(ES_vol / 2 + 20, reservoir[well].top(-2), push_out=10)
    pte.blow_out()
    pte.blow_out()


def ES_addition_1(pte, ES_asp, ES_disp, ES_blow, ES_tip, ES_vol,
                  reservoir, protocol, dest_plate, well):
    """
    Delivers the first 600uL of extraction solvent (half of ES_vol) to the
    destination plate.

    Solvent is dispensed from 10mm below the well top to encourage mixing
    with the sample below. A tip-wipe across the well rim removes any hanging
    droplet from the outside of the tip after dispense.

    Parameters
    ----------
    pte        : pipette object
    ES_asp     : aspirate flow rate (uL/sec)
    ES_disp    : dispense flow rate (uL/sec)
    ES_blow    : blow-out flow rate (uL/sec)
    ES_tip     : tip rack labware object (tips already loaded from prewet step)
    ES_vol     : total extraction solvent volume (uL); half is delivered here
    reservoir  : source labware (NEST 195mL reservoir)
    protocol   : protocol context
    dest_plate : destination labware (Abgene 2.2mL plate)
    well       : well address string (e.g. 'A1')
    """
    pte.flow_rate.aspirate = ES_asp
    pte.flow_rate.dispense = ES_disp
    pte.flow_rate.blow_out = ES_blow

    # Delivery of first half of ES
    # Aspirate 1mm above reservoir bottom to avoid drawing in air
    pte.aspirate(ES_vol / 2, reservoir[well].bottom(1))
    pte.move_to(reservoir[well].top(), speed=50)
    pte.air_gap(20)

    # Dispense 10mm below the well top; push_out=10 ensures complete delivery
    pte.dispense(ES_vol / 2 + 20, dest_plate[well].top(-10), push_out=10)
    pte.blow_out()
    pte.blow_out()

    # Tip-wipe: sweep the tip laterally across the well rim to shear off any hanging droplet
    pte.move_to(dest_plate[well].top(-1))
    pte.move_to(dest_plate[well].top(-1).move(types.Point(y=4.2)))
    pte.move_to(dest_plate[well].top(-1).move(types.Point(y=-4.2)))


def ES_addition_2(pte, ES_asp, ES_disp, ES_blow, ES_tip, ES_vol,
                  reservoir, protocol, dest_plate, well):
    """
    Delivers the second 600uL of extraction solvent (half of ES_vol) to the
    destination plate.

    Identical to ES_addition_1 except that the tip descends to 5mm above the
    well bottom before the tip-wipe. This additional move helps dislodge any
    liquid clinging to the tip exterior after the second delivery.

    Parameters
    ----------
    pte        : pipette object
    ES_asp     : aspirate flow rate (uL/sec)
    ES_disp    : dispense flow rate (uL/sec)
    ES_blow    : blow-out flow rate (uL/sec)
    ES_tip     : tip rack labware object (tips already loaded from prewet step)
    ES_vol     : total extraction solvent volume (uL); half is delivered here
    reservoir  : source labware (NEST 195mL reservoir)
    protocol   : protocol context
    dest_plate : destination labware (Abgene 2.2mL plate)
    well       : well address string (e.g. 'A1')
    """
    pte.flow_rate.aspirate = ES_asp
    pte.flow_rate.dispense = ES_disp
    pte.flow_rate.blow_out = ES_blow

    # Delivery of second half of ES
    # Aspirate 1mm above reservoir bottom to avoid drawing in air
    pte.aspirate(ES_vol / 2, reservoir[well].bottom(1))
    pte.move_to(reservoir[well].top(), speed=50)
    pte.air_gap(20)

    # Dispense 10mm below the well top; push_out=10 ensures complete delivery
    pte.dispense(ES_vol / 2 + 20, dest_plate[well].top(-10), push_out=10)
    pte.blow_out()
    pte.blow_out()

    # Dip tip toward well bottom before wipe to help shed liquid from the tip exterior
    pte.move_to(dest_plate[well].bottom(5))

    # Tip-wipe: sweep the tip laterally across the well rim to shear off any hanging droplet
    pte.move_to(dest_plate[well].top(-1))
    pte.move_to(dest_plate[well].top(-1).move(types.Point(y=4.2)))
    pte.move_to(dest_plate[well].top(-1).move(types.Point(y=-4.2)))
