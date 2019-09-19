#include <libgen.h>
#include <linux/limits.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

// This generates PGM images from a large input binary file.
//
// This was written by someone who doesn't know shit about C.
// This person knows he's bad, but also has feelings.

/* Generates the .pgm file.
 *
 * It will be width x height, with bytes taken from source, starting at offset offset.
 */
int convert(const char *source_path, const char *destination_path, long width, long height, long offset) {
  int i, j;
  FILE *destp = fopen(destination_path, "wb");
  FILE *sourcep = fopen(source_path, "rb");
  if (destp == NULL) {
      printf("Could not open %s for writing\n", destination_path);
      return EXIT_FAILURE;
  }
  if (sourcep == NULL) {
      printf("Could not open %s for reading\n", source_path);
      return EXIT_FAILURE;
  }
  // Go to the offset
  fseek(sourcep, offset, SEEK_SET);
  // Let's write this PGM file. First, the header
  printf("Writing %s\n", destination_path);
  fprintf(destp, "P5\n%ld %ld\n255\n", width, height);
  for (j = 0; j < width; ++j)
  {
    for (i = 0; i < height; ++i)
    {
      // Very unefficient 1-by-1 byte reading lol
      int c = fgetc(sourcep);
      if (c != EOF) {
        int result = fwrite(&c, 1, 1, destp);
        if (result != 1) {
            perror("Error: ");
            fclose(destp);
            fclose(sourcep);
            return 1;
        }
      }
    }
  }
  fclose(destp);
  fclose(sourcep);
  return EXIT_SUCCESS;
}

int usage() {
  printf("Usage: %s <input_file> <page_size> <dest_directory> [columns]\n", __FILE__);
  printf("Generates <columns> PGM files where 1 pixel represent the value of one byte in the dump\n");
  return EXIT_FAILURE;
}
 
int main(int argc, char **argv) {
  struct stat st;
  long inputfile_size = 0;
  long page_size = 0;
  int filesplit_number = 8;
  int res = 0;

  char *inputfile_path = argv[1];
  char *destdir_path = argv[3];

  if (argc == 1 || (strncmp(argv[1], "--help", 6)==0) || (strncmp(argv[1], "-h", 6) == 0)) {
      return usage();
  }

  if (argc < 4) {
      return usage();
  }

  res = stat(inputfile_path, &st);
  if (res != 0) {
      printf("ERROR: can't read input file size: '%s'\n", inputfile_path);
      return EXIT_FAILURE;
  }

  // Some input file size sanity checks
  inputfile_size = st.st_size;
  page_size = strtol(argv[2], NULL, 10);
  if ((page_size < 1) || (page_size > 1*1024*1024)) {
      printf("Invalid page size: '%s'\n", argv[2]);
      return EXIT_FAILURE;
  }
  printf("%d\n",filesplit_number);
  if (inputfile_size % page_size != 0) {
      printf("WARNING: %s is of size %ld, which is not a multiple of page size %ld\n", inputfile_path, inputfile_size, page_size);
      printf("WARNING: We might be losing some data\n");
  }

  if (argc == 5) {
      filesplit_number = strtol(argv[4], NULL, 10);
  }

  const int dimx = page_size;
  const long pixels_by_pic = inputfile_size / filesplit_number;
  const int dimy = pixels_by_pic / dimx;

  char *inputfile_name = basename(inputfile_path);
  printf("I'll generate %d PGM files for file %s\n", filesplit_number, inputfile_name);

  char *dest_picture_path = (char *)malloc(PATH_MAX);
  long offset = 0;
  for (int i=0; i < filesplit_number; i++) {
      // the output PGM files are goint go look like
      // dest_dir/dump.bin_0_start-end.pgm
      snprintf(dest_picture_path, PATH_MAX, "%s/%s_%d_%ld-%ld.pgm", destdir_path, inputfile_name, i, offset, offset+pixels_by_pic);
      res = convert(inputfile_name, dest_picture_path, dimx, dimy, offset);
      if (res != 0 ) {
          printf("ERROR trying to convert %s\n", dest_picture_path);
          free(dest_picture_path);
          return res;
      }

      offset += pixels_by_pic;
  }
  free(dest_picture_path);

  return EXIT_SUCCESS;
}
