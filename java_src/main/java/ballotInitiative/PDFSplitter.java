package ballotInitiative;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

import org.apache.pdfbox.multipdf.Splitter;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;

public class PDFSplitter {

    private static final String INPUT_DIR = "C:\\Users\\lpert\\git\\DC Civic Tech\\Ballot Initiative\\Ballot Inititive Scans";
    private static final String INPUT_FILE = "initiative_scans.pdf";
    private static final String OUTPUT_DIR = "Split Documents";
    private static PDPage templatePage;

    public static void main(String[] args) {
        try {
            File inputFile = new File(INPUT_DIR, INPUT_FILE);
            try (PDDocument document = PDDocument.load(inputFile)) {
                templatePage = document.getPage(document.getNumberOfPages() - 1); // Save the last page as template
                splitDocument(document);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private static void splitDocument(PDDocument document) throws IOException {
        Splitter splitter = new Splitter() {    
            @Override
            protected PDDocument createNewDocument() throws IOException {
                PDDocument newDoc = super.createNewDocument();
                // Add the template page as the last page of each new document
                newDoc.addPage(templatePage);
                return newDoc;
            }
        };

        splitter.setSplitAtPage(1); // Split every 1 page, plus the template page makes 3

        List<PDDocument> pages = splitter.split(document);
        
        Path outputDirectory = Paths.get(OUTPUT_DIR);
        Files.createDirectories(outputDirectory); // Ensure the output directory exists

        int fileCount = 1;
        for (PDDocument doc : pages) {
            Path outputFile = outputDirectory.resolve("split_document_" + fileCount++ + ".pdf");
            doc.save(outputFile.toFile());
            doc.close();
        }

    }
}
