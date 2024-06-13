package ballotInitiative;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

public class DirectoryCleaner {

    public static void deleteContents(String directoryPath) throws IOException {
        Path path = Paths.get(directoryPath);
        try {

            // Iterate over each file/directory inside the specified directory
            Files.walk(path)
                    .filter(subPath -> !subPath.equals(path)) // Exclude the root directory itself
                    .forEach(subPath -> {
                        try {
                            Files.delete(subPath); // Delete each file/directory
                        } catch (IOException e) {
                            System.err.println("Failed to delete: " + subPath);
                            e.printStackTrace();
                        }
                    });
        } catch (IOException e) {
            System.err.println("Failed to create directory: " + path);
            e.printStackTrace();
            return;
        }
    }
}
