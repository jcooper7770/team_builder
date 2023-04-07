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


def fill_out(data, filename="modified_comp_card.pdf"):
    """
    Fill out the comp card with the data
    """
    generate_fields_obj()

    # Open the PDF file
    pdf_doc = fitz.open(PDF_FILE)
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

    fill_out(data)