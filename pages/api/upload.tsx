const formidable= require('formidable');
import fs from 'fs';
import { originalPathname } from 'next/dist/build/templates/app-page';
import path from 'path';


// Function to split the directory path into individual folder names
const splitDirectoryPath = (dirPath: string): string[] => {
  // Normalize the path (remove any trailing slashes) and split it into parts
  const normalizedPath = path.normalize(dirPath);  // Normalize to handle any irregularities
  const folderParts = normalizedPath.split(path.sep); // `path.sep` is OS-specific separator
  const partsWithoutEmptyStrings = folderParts.filter(part => part !== '');

  // Remove the last part from the array
  partsWithoutEmptyStrings.pop();

  return partsWithoutEmptyStrings;
};
export const config = {
  api: {
    bodyParser: false, // Disable default body parser to handle file upload manually
  },
};

const uploadFolderHandler = (req: any, res: any) => {
  const form = new formidable.IncomingForm({'allowEmptyFiles':true,'minFileSize': 0});

  // Handle form parsing and directory validation
  form.keepExtensions = true; // Keep original file extensions
  form.allowEmptyFiles = true; 
  form.parse(req, (err: any, fields: any, files: any) => {
    if (err) {
      console.error('Error parsing files:', err);
      return res.status(500).json({ error: 'File upload failed' });
    }

    const directoryName = Array.isArray(fields.directoryName) ? fields.directoryName[0] : fields.directoryName;
    // Sanitize directory name (to avoid path traversal and invalid names)
    if (!directoryName || !/^[a-zA-Z0-9_-]+$/.test(directoryName)) {
      return res.status(400).json({ error: 'Invalid directory name' });
    }

    // Create the full path to the upload directory based on user input
    var uploadDir = path.join(process.cwd(), 'repos', directoryName);

    //console.log('Uploading to:', uploadDir);

    // Ensure the target directory exists
    if (!fs.existsSync(uploadDir)) {
      try {
        fs.mkdirSync(uploadDir, { recursive: true }); // Create the directory if it doesn't exist
      } catch (mkdirError) {
        console.error('Error creating directory:', mkdirError);
        return res.status(500).json({ error: 'Failed to create directory' });
      }
    }
    var uploadDir = path.join(process.cwd(), 'repos')
    // Custom filename function to ensure original filenames
    form.filename = (name, ext, part, form) => {
      const originalFilename = part.originalFilename;
      if (originalFilename) {
        // Optionally, generate a unique filename here (e.g., using timestamp)
        const uniqueName = `${Date.now()}-${originalFilename}`;
        return uniqueName;
      }
      return name + ext; // Fallback
    };

    // Process files after parsing
    const uploadedFiles: string[] = [];

    Object.values(files).forEach((fileOrArray: any) => {
      const fileList = Array.isArray(fileOrArray) ? fileOrArray : [fileOrArray];

      fileList.forEach((file: any) => {
        const originalFilename = file.originalFilename;
        if (!originalFilename) {
          console.error('Filename is missing or invalid');
          return;
        }
        var folderParts = splitDirectoryPath(originalFilename);
        let currentPath = path.join(process.cwd(), 'repos'); 
        folderParts.forEach((folder) => {
            currentPath = path.join(currentPath, folder); // Join the current path with the folder
            if (!fs.existsSync(currentPath)) {
              try {
                fs.mkdirSync(currentPath, { recursive: true }); // Create the directory if it doesn't exist
                console.log(`Directory created: ${currentPath}`);
              } catch (mkdirError) {
                console.error('Error creating directory:', mkdirError);
                throw new Error('Failed to create directory');
              }
            }
          });
        const targetPath = path.join(uploadDir, originalFilename);

        try {
          // Move the file from the temporary location to the target location
          fs.renameSync(file.filepath, targetPath);
          uploadedFiles.push(originalFilename); // Keep track of uploaded files
        } catch (moveError) {
          console.error('Error moving file:', moveError);
          return res.status(500).json({ error: 'Failed to move file' });
        }
      });
    });

    // Respond with success message and uploaded file names
    return res.status(200).json({ message: 'Files uploaded successfully', files: uploadedFiles });
  });
};

export default uploadFolderHandler;
