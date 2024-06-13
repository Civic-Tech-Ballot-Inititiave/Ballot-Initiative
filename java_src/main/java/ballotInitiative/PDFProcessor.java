package ballotInitiative;

import java.awt.geom.Rectangle2D;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;

import javax.imageio.ImageIO;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.graphics.image.PDImageXObject;
import org.apache.pdfbox.rendering.PDFRenderer;

public class PDFProcessor {

    private Rectangle2D cropBox;

    public PDFProcessor() {

    }

    public PDFProcessor(Rectangle2D cropBox) {
        this.cropBox = cropBox;
    }

    protected void cropFirstPagePNG(String imagePath, String outputDir, Rectangle2D cropBox) throws IOException {
        BufferedImage originalImage = ImageIO.read(new File(imagePath));
        BufferedImage croppedImage = originalImage.getSubimage(
                (int) cropBox.getX(),
                (int) cropBox.getY(),
                (int) cropBox.getWidth(),
                (int) cropBox.getHeight());

        File outputFile = new File(outputDir, "cropped_first_page.png");
        ImageIO.write(croppedImage, "png", outputFile);
    }

    protected void cropAndSaveAsPNG(String inputDir, String outputDir) throws IOException {
        File[] files = new File(inputDir).listFiles((dir, name) -> name.toLowerCase().endsWith(".png"));
        if (files == null) {
            throw new IOException("No PNG files found in the input directory.");
        }

        for (int i = 0; i < files.length; i++) {
            BufferedImage bim = ImageIO.read(files[i]);

            BufferedImage croppedImage = bim.getSubimage(
                    (int) cropBox.getX(),
                    (int) cropBox.getY(),
                    (int) cropBox.getWidth(),
                    (int) cropBox.getHeight());

            File outputFile = new File(outputDir, "cropped_image_" + i + ".png");
            ImageIO.write(croppedImage, "png", outputFile);
        }
    }

    /*
     * protected void cropAndSaveAsPNG(String inputPath, String outputDir) throws
     * IOException {
     * try (PDDocument document = Loader.loadPDF(new File(inputPath))) {
     * PDFRenderer pdfRenderer = new PDFRenderer(document);
     * for (int page = 0; page < document.getNumberOfPages(); ++page) {
     * BufferedImage bim = pdfRenderer.renderImageWithDPI(page, 300);
     * BufferedImage croppedImage = bim.getSubimage(
     * (int) cropBox.getX(),
     * (int) cropBox.getY(),
     * (int) cropBox.getWidth(),
     * (int) cropBox.getHeight());
     * 
     * File outputFile = new File(outputDir, "cropped_page_" + page + ".png");
     * ImageIO.write(croppedImage, "png", outputFile);
     * }
     * }
     * 
     * }
     */

    protected static void combineImagesIntoPDF(String[] imagePaths, String outputPath) throws IOException {
        try (PDDocument document = new PDDocument()) {
            for (String imagePath : imagePaths) {
                BufferedImage image = ImageIO.read(new File(imagePath));
                if (image == null) {
                    throw new IOException("Could not read image from path: " + imagePath);
                }
                PDPage page = new PDPage(new PDRectangle(image.getWidth(), image.getHeight()));
                document.addPage(page);

                PDImageXObject pdImage = PDImageXObject.createFromFile(imagePath, document);
                try (PDPageContentStream contentStream = new PDPageContentStream(document, page)) {
                    // Draw the image at full size at position (0,0)
                    contentStream.drawImage(pdImage, 0, 0, image.getWidth(), image.getHeight());
                }
            }
            document.save(outputPath);
        }
    }

    public static void convertPDFToPNG(String inputPath, String outputDir) throws IOException {
        try (PDDocument document = Loader.loadPDF(new File(inputPath))) {
            PDFRenderer pdfRenderer = new PDFRenderer(document);
            for (int page = 0; page < document.getNumberOfPages(); ++page) {
                BufferedImage bim = pdfRenderer.renderImageWithDPI(page, 300); // Render with a DPI of 300
                File outputFile = new File(outputDir, "page_" + page + ".png");
                ImageIO.write(bim, "png", outputFile);
            }
        }
    }

}
