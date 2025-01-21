# Sample Data Files

This directory contains sample data files used for testing and development of the Ballot Initiative project.

## Files

#### `fake_voter_records.csv`

A sample CSV file containing 100,000 rows of synthetic voter data with the following columns:

- `First_Name`
- `Last_Name`
- `Street_Number`
- `Street_Name`
- `Street_Type`
- `Street_Dir_Suffix`

#### `spurious_signers.csv`

A sample CSV file containing 100 rows of synthetic voter data. The columns are the same as the `fake_voter_records.csv` file.

However, the "voters" in this file are ones who are NOT in the `fake_voter_records.csv` file, and thus represent spurious signatures (i.e., non-registered voters) that the algorithm should not match.

#### `all_petition_signers.csv`

A CSV file containing 400 randomly selected rows from the `fake_voter_records.csv` file, and all of the rows from the `spurious_voter_records.csv` file. The columns are the same as the `fake_voter_records.csv` file.

This file contains ~500 sample records and is used to test the signature validation and matching functionality. The data is randomly generated and does not represent real voter information.

#### `fake_signed_petitions.pdf`

A sample PDF file containing 100 pages of simulated ballot initiative petition signatures from the people listed in `all_petition_signers.csv`. This file is used for testing the OCR functionality of the application. The PDF contains scanned images of signatures and voter information in a format similar to real ballot initiative petitions.

#### `fake_signed_petitions_1-10.pdf`

The first 10 pages of the `fake_signed_petitions.pdf` file. Used for quicker processing.

## Usage

These files are intended for development and testing purposes only. The data format matches what the application expects but contains synthetic information rather than real voter data.

To use these files:

1. For OCR testing:

   - Use `fake_signed_petitions_1-10.pdf` as input when testing the PDF processing and OCR functionality
   - The file contains 10 pages to test batch processing capabilities

2. For voter matching:
   - Use `all_petition_signers.csv` as a test voter database
   - The file follows the same schema as the real voter records but with fake data
   - Useful for testing the fuzzy matching algorithms without requiring access to actual voter records

## Notes

- **All** data in these files is synthetic and generated for testing purposes; Any resemblance to real voter data is coincidental.
- These samples can be used without permission, but if you use them in a project, please cite this repository.
