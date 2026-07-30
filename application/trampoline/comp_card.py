#import PyPDF2
import fitz
import os

PDF_FILE = "comp_card_trampoline.pdf"
FIELDS = {
    "name": {
        'pos': (100, 195),
        'size': 24
    },
    'vol1skill1': {
        'pos': (100, 270),
        'size': 12
    },
    'vol1skill2': {
        'pos': (100, 289),
        'size': 12
    },
    'vol1skill3': {
        'pos': (100, 308),
        'size': 12
    }

}

def generate_fields_obj():
    """
    create fields positions
    """
    global FIELDS
    fields = {
        "name": {'pos': (100, 195), 'size': 24},
        'team': {'pos': (390, 150), 'size': 24},
        'coaches': {'pos': (390, 195), 'size': 24},
        'gender': {'pos': (535, 62), 'size': 12},
        'level': {'pos': (535, 84), 'size': 12},
        'age': {'pos': (535, 106), 'size': 12},
    }
    for num in range(10):
        # first routine
        fields[f'vol1skill{num+1}'] = {
            'pos': (100, 270 + 18*num),
            'size': 12
        }
        fields[f'vol1skill{num+1}dd'] = {
            'pos': (197, 270 + 18*num),
            'size': 12
        }
        fields['vol1total'] = {
            'pos': (150, 455),
            'size': 12
        }

        # second routine
        fields[f'vol2skill{num+1}'] = {
            'pos': (365, 270 + 18*num),
            'size': 12
        }
        fields[f'vol2skill{num+1}dd'] = {
            'pos': (462, 270 + 18*num),
            'size': 12
        }
        fields['vol2total'] = {
            'pos': (420, 455),
            'size': 12
        }

        # finals routine
        fields[f'finalsskill{num+1}'] = {
            'pos': (100, 538 + 18*num),
            'size': 12
        }
        fields[f'finalsskill{num+1}dd'] = {
            'pos': (197, 538 + 18*num),
            'size': 12
        }
        fields['finalstotal'] = {
            'pos': (150, 723),
            'size': 12
        }
    FIELDS = fields


def generate_dmt_fields_obj():
    """
    Generate the FIELDS obj for the double mini comp card
    """
    global FIELDS
    fields = {
        "name": {'pos': (110, 175), 'size': 24},
        'team': {'pos': (400, 140), 'size': 24},
        'coaches': {'pos': (400, 175), 'size': 24},
        'gender': {'pos': (535, 42), 'size': 12},
        'level': {'pos': (535, 64), 'size': 12},
        'age': {'pos': (535, 86), 'size': 12},
    }

    # prelims pass 1
    fields["prelims_pass1_mounter"] = {'pos': (150, 265), 'size': 14}
    fields["prelims_pass1_mounter_dd"] = {'pos': (150, 290), 'size': 14}
    fields["prelims_pass1_spotter"] = {'pos': (215, 265), 'size': 14}
    fields["prelims_pass1_spotter_dd"] = {'pos': (215, 290), 'size': 14}
    fields["prelims_pass1_dismount"] = {'pos': (285, 265), 'size': 14}
    fields["prelims_pass1_dismount_dd"] = {'pos': (285, 290), 'size': 14}
    fields["prelims_pass1_total"] = {'pos': (360, 275), 'size': 20}

    # prelims pass 2
    fields["prelims_pass2_mounter"] = {'pos': (150, 407), 'size': 14}
    fields["prelims_pass2_mounter_dd"] = {'pos': (150, 430), 'size': 14}
    fields["prelims_pass2_spotter"] = {'pos': (215, 407), 'size': 14}
    fields["prelims_pass2_spotter_dd"] = {'pos': (215, 430), 'size': 14}
    fields["prelims_pass2_dismount"] = {'pos': (285, 407), 'size': 14}
    fields["prelims_pass2_dismount_dd"] = {'pos': (285, 430), 'size': 14}
    fields["prelims_pass2_total"] = {'pos': (360, 418), 'size': 20}

    # finals pass 1
    fields["finals_pass1_mounter"] = {'pos': (150, 549), 'size': 14}
    fields["finals_pass1_mounter_dd"] = {'pos': (150, 572), 'size': 14}
    fields["finals_pass1_spotter"] = {'pos': (215, 549), 'size': 14}
    fields["finals_pass1_spotter_dd"] = {'pos': (215, 572), 'size': 14}
    fields["finals_pass1_dismount"] = {'pos': (285, 549), 'size': 14}
    fields["finals_pass1_dismount_dd"] = {'pos': (285, 572), 'size': 14}
    fields["finals_pass1_total"] = {'pos': (360, 560), 'size': 20}

    # finals pass 2
    fields["finals_pass2_mounter"] = {'pos': (150, 691), 'size': 14}
    fields["finals_pass2_mounter_dd"] = {'pos': (150, 714), 'size': 14}
    fields["finals_pass2_spotter"] = {'pos': (215, 691), 'size': 14}
    fields["finals_pass2_spotter_dd"] = {'pos': (215, 714), 'size': 14}
    fields["finals_pass2_dismount"] = {'pos': (285, 691), 'size': 14}
    fields["finals_pass2_dismount_dd"] = {'pos': (285, 714), 'size': 14}
    fields["finals_pass2_total"] = {'pos': (360, 702), 'size': 20}

    FIELDS = fields


def generate_tumbling_fields_obj():
    pass


def fill_out(data, filename="modified_comp_card.pdf", event="trampoline"):
    """
    Fill out the comp card with the data
    """
    if event == "trampoline":
        generate_fields_obj()
    elif event == "dm":
        generate_dmt_fields_obj()
    elif event == "tumbling":
        generate_tumbling_fields_obj()

    # Open the PDF file
    #pdf_doc = fitz.open(PDF_FILE)
    pdf_doc = fitz.open(f"comp_card_{event}.pdf")
    # Get the first page of the PDF file
    page = pdf_doc[0]
    text_color = (0, 0, 0)  # black
    text_font = "Helvetica-Bold"

    for field, value in data.items():
        if field not in FIELDS:
            print(f"Skipping field {field} from comp card. Not in fields: {FIELDS.keys()}")
            continue

        comp_field_value = FIELDS[field]
        page.insert_text(
            comp_field_value['pos'], value,
            fontname=text_font,
            fontsize=comp_field_value['size'],
            color=text_color
        )

    # Save the modified PDF file
    if not os.path.exists("comp_cards"):
        os.mkdir("comp_cards")

    file_path = os.path.join("comp_cards", filename)
    pdf_doc.save(file_path)

if __name__ == '__main__':
    comp_card_file = "comp_card_trampoline.pdf"
    generate_fields_obj()

    '''
    routine_skills = [
        ('12001<', '2.0'),
        ('811<', '1.4'),
        ('12001o', '1.7'),
        ('811o', '1.2'),
        ('803<', '1.5'),
        ('800o', '1.0'),
        ('803o', '1.3'),
        ('800<', '1.2'),
        ('801<', '1.3'),
        ('822/', '1.6'),
    ]
    data = {
        'name': 'Jeremy Cooper',
        'team': 'World Elite',
        'coaches': "Logan Dooley",
        'gender': 'M',
        'age': 'N/A',
        'level': 'Sr',
        'vol1skill1': '12001<',
        'vol1skill1dd': '2.0',
        'vol1skill2': '811<',
        'vol1skill2dd': '1.4',
        'vol1skill3': '12001o',
        'vol1skill3dd': '1.7',
        'vol1skill4': '811o',
        'vol1skill4dd': '1.2',
        'vol1total': '14.2',
        'vol2total': '14.2',
        'finalstotal': '14.2',
    }
    for num, skill in enumerate(routine_skills):
        data[f'vol1skill{num+1}'] = skill[0]
        data[f'vol1skill{num+1}dd'] = skill[1]
        data[f'vol2skill{num+1}'] = skill[0]
        data[f'vol2skill{num+1}dd'] = skill[1]
        data[f'finalsskill{num+1}'] = skill[0]
        data[f'finalsskill{num+1}dd'] = skill[1]
    '''
    passes = [
        ("801<", "2.8"),
        ("822/", "4.4")
    ]
    data = {
        'name': 'Jeremy Cooper',
        'team': 'World Elite',
        'coaches': "Logan Dooley",
        'gender': 'M',
        'age': 'N/A',
        'level': 'Sr',
        "prelims_pass1_mounter": "801<",
        "prelims_pass1_mounter_dd": "2.8",
        "prelims_pass1_dismount": "822/",
        "prelims_pass1_dismount_dd": "4.4",
        "prelims_pass1_total": "7.2",
        "prelims_pass2_mounter": "803<",
        "prelims_pass2_mounter_dd": "3.6",
        "prelims_pass2_dismount": "813<",
        "prelims_pass2_dismount_dd": "4.0",
        "prelims_pass2_total": "7.6",
        "finals_pass1_mounter": "803<",
        "finals_pass1_mounter_dd": "3.6",
        "finals_pass1_dismount": "813<",
        "finals_pass1_dismount_dd": "4.0",
        "finals_pass1_total": "7.6",
        "finals_pass2_spotter": "803<",
        "finals_pass2_spotter_dd": "3.6",
        "finals_pass2_dismount": "813<",
        "finals_pass2_dismount_dd": "4.0",
        "finals_pass2_total": "7.6",
    }

    fill_out(data, event="dm")