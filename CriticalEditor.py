import os
import csv
from collections import defaultdict
from docx import Document


# Function to load CSV data
def load_csv(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        headers = next(reader)  # Get the headers
        data = [row for row in reader]  # Read the remaining data
    return headers, data


def create_critical_edition(csv_data, headers):
    doc = Document()

    for row in csv_data:
        line_variations = defaultdict(list)

        for i, line in enumerate(row):
            line_variations[line].append(headers[i])

        # Remove blank line entry for processing
        blank_line_editions = line_variations.pop('', None)

        # Find the most common line (excluding blanks)
        if line_variations:
            most_common_line, editions_with_most_common = max(line_variations.items(), key=lambda item: len(item[1]))
        else:
            most_common_line, editions_with_most_common = None, []

        # Rule 1: Add line if it's the same across all editions
        if len(line_variations) == 0:
            doc.add_paragraph(most_common_line)
            continue

        # Add the most common line
        if most_common_line:
            doc.add_paragraph(most_common_line)

        # Rule 3: Handle variations, including blanks
        for line, editions in line_variations.items():
            if line != most_common_line:  # Exclude the most common line
                editions_str = ', '.join(editions)
                doc.add_paragraph(f"({editions_str} reads as: '{line}')")

        # Include blank line information if it exists
        if blank_line_editions:
            blank_editions_str = ', '.join(blank_line_editions)
            doc.add_paragraph(f"(There is no line in {blank_editions_str} here)")

    return doc


# Your existing load_csv and create_critical_edition functions go here

def process_csv_folder(source_folder_path, output_folder_path):
    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    for filename in os.listdir(source_folder_path):
        if filename.endswith('.csv'):
            csv_file_path = os.path.join(source_folder_path, filename)
            headers, csv_data = load_csv(csv_file_path)
            
            critical_edition_doc = create_critical_edition(csv_data, headers)
            
            output_docx_path = os.path.join(output_folder_path, f"{os.path.splitext(filename)[0]}_critical_edition.docx")
            critical_edition_doc.save(output_docx_path)
            print(f"Processed and saved: {filename}")

# Example usage
source_folder = '/Users/enesyilandiloglu/Documents/GitHub/Kakule_1/CompLit/AlignedPoems'  # Replace with your source folder path
output_folder = '/Users/enesyilandiloglu/Documents/GitHub/Kakule_1/CompLit/CriticalEditions'  # Replace with your desired output folder path
process_csv_folder(source_folder, output_folder)
