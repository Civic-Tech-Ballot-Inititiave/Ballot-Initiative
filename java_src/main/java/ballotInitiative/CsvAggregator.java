package ballotInitiative;

import java.io.*;
import java.nio.file.*;
import java.util.*;

public class CsvAggregator {

	private static final String directoryPath = "C:\\Users\\lpert\\git\\DC Civic Tech\\Ballot Initiative\\Split CSVs";
	private static final String outputPath = "C:\\Users\\lpert\\git\\DC Civic Tech\\Ballot Initiative\\Aggregated Data\\output.csv"; // Replace with your desired output file path

    public static void main(String[] args) throws IOException {
    	
        File dir = new File(directoryPath);
        File[] directoryListing = dir.listFiles();
        List<List<String>> records = new ArrayList<>();

        if (directoryListing != null) {
            for (File child : directoryListing) {
                // Check if the file is a CSV file
                if (child.isFile() && child.getName().endsWith(".csv")) {
                    List<List<String>> fileRecords = readCsv(child.getPath());
                    if (!fileRecords.isEmpty()) {
                        // Skip header for subsequent files
                        if (!records.isEmpty()) {
                            fileRecords.remove(0);
                        }
                        records.addAll(fileRecords);
                    }
                }
            }
        }

        writeCsv(outputPath, records);
    }

    private static List<List<String>> readCsv(String filePath) throws IOException {
        List<List<String>> records = new ArrayList<>();
        try (BufferedReader br = Files.newBufferedReader(Paths.get(filePath))) {
            String line;
            while ((line = br.readLine()) != null) {
                String[] values = line.split(",");
                records.add(Arrays.asList(values));
            }
        }
        return records;
    }

    private static void writeCsv(String filePath, List<List<String>> records) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(Paths.get(filePath))) {
            for (List<String> record : records) {
                writer.write(String.join(",", record));
                writer.newLine();
            }
        }
    }
}
