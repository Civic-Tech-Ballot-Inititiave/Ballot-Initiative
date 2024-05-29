package ballotInitiative;

import java.awt.geom.Rectangle2D;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import javax.imageio.ImageIO;

public class MainApplication {
    private final static String initiativeScansInputLocation = "C:\\Users\\lpert\\git\\DC Civic Tech\\Ballot Initiative\\Ballot Inititive Scans\\input\\initiative_scans.pdf";
    private final static String initiativeScansOutputFile = "C:\\Users\\lpert\\git\\DC Civic Tech\\Ballot Initiative\\Ballot Inititive Scans\\output\\cropped_ballots.pdf";
    private final static String initiativeScansOutputLocation = "C:\\Users\\lpert\\git\\DC Civic Tech\\Ballot Initiative\\Ballot Inititive Scans\\output\\";
    private final static String initiativeScansPDFToPNG = "C:\\Users\\lpert\\git\\DC Civic Tech\\Ballot Initiative\\Ballot Inititive Scans\\PDFToPNG\\";
    private final static String initiativeScansCroppedImagesLocation = "C:\\Users\\lpert\\git\\DC Civic Tech\\Ballot Initiative\\Ballot Inititive Scans\\CroppedImages\\";

    // private final static String initiativeScansInputLocation = "Ballot Initiative
    // Scans\\input\\initiative_scans.pdf";
    // private final static String initiativeScansOutputFile = "Ballot Initiative
    // Scans\\output\\cropped_ballots.pdf";
    // private final static String initiativeScansOutputLocation = "Ballot
    // Initiative Scans\\output\\";
    // private final static String initiativeScansPDFToPNG = "Ballot Initiative
    // Scans\\PDFToPNG";
    // private final static String initiativeScansCroppedImagesLocation = "Ballot
    // Initiative Scans\\CroppedImages\\";

    public static void main(String[] args) {
        try {
            // Clean the intermediary directories
            System.out.println("Current working directory: " + System.getProperty("user.dir"));

            DirectoryCleaner.deleteContents(initiativeScansPDFToPNG);
            DirectoryCleaner.deleteContents(initiativeScansCroppedImagesLocation);
            DirectoryCleaner.deleteContents(initiativeScansOutputLocation);
            // Convert the pdf to png
            PDFProcessor.convertPDFToPNG(initiativeScansInputLocation, initiativeScansPDFToPNG);
            // Create and display the CropGUI
            File firstPageFile = new File(initiativeScansPDFToPNG + "page_0.png");
            if (!firstPageFile.exists()) {
                System.err.println("First page PNG file not found.");
                return;
            }
            BufferedImage firstPageImage = ImageIO.read(firstPageFile);

            new CropGUI(firstPageImage, cropArea -> {
                try {
                    // Process the PDF using the selected crop area
                    Rectangle2D rect = new Rectangle2D.Double(cropArea.x, cropArea.y, cropArea.width, cropArea.height);
                    PDFProcessor pdfProcessor = new PDFProcessor(rect);
                    pdfProcessor.cropAndSaveAsPNG(initiativeScansPDFToPNG, initiativeScansCroppedImagesLocation);
                    System.out.println("Finished Cropping Images");
                    recombineCroppedImages();
                } catch (IOException e) {
                    e.printStackTrace();
                }
            });

        } catch (IOException e) {
            e.printStackTrace();
        }

    }

    private static void recombineCroppedImages() {
        try {
            // Get all files in the specified directory
            File directory = new File(initiativeScansCroppedImagesLocation);
            File[] files = directory.listFiles();

            if (files != null) {
                List<String> imagePaths = new ArrayList<>();

                // Loop through each file in the directory
                for (File file : files) {
                    // Check if it's a file (not a directory)
                    if (file.isFile()) {
                        // Add the file path to the list of image paths
                        imagePaths.add(file.getAbsolutePath());
                    }
                }

                PDFProcessor.combineImagesIntoPDF(imagePaths.toArray(new String[0]), initiativeScansOutputFile);

                System.out.println("Combined PDF created successfully!");
            } else {
                System.out.println("No files found in the specified directory.");
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
