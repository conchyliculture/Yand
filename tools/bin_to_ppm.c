#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

// This generates PGM images from a large input binary file.

//void convert_xor(const char *source1, const char *source2, const char *dest, int width, int height, int offset) {
//  int i, j;
//  FILE *destp = fopen(dest, "wb"); /* b - binary mode */
//  FILE *sourcep1 = fopen(source1, "rb"); /* b - binary mode */
//  FILE *sourcep2 = fopen(source2, "rb"); /* b - binary mode */
//  printf("Writing %s\n", dest);
//  (void) fprintf(destp, "P5\n%d %d\n255\n", width, height);
//  fseek(sourcep1, offset, SEEK_SET);
//  fseek(sourcep2, offset, SEEK_SET);
//  for (j = 0; j < width; ++j)
//  {
//    for (i = 0; i < height; ++i)
//    {
//      int c1 = fgetc(sourcep1);
//      int c2 = fgetc(sourcep2);
//      int c3 = c1^c2;
//
//      (void) fwrite(&c3, 1, 1, destp);
//    }
//  }
//  (void) fclose(destp);
//  (void) fclose(sourcep1);
//  (void) fclose(sourcep2);
//}


/* Generates the .pgm file.
 *
 * It will be width x height, with bytes taken from source, starting at offset offset.
 */
void convert(const char *source, const char *dest, int width, int height, int offset) {
  int i, j;
  FILE *destp = fopen(dest, "wb");
  FILE *sourcep = fopen(source, "rb");
  (void) fprintf(destp, "P5\n%d %d\n255\n", width, height);
  fseek(sourcep, offset, SEEK_SET);
  printf("Writing %s\n", dest);
  for (j = 0; j < width; ++j)
  {
    for (i = 0; i < height; ++i)
    {
      unsigned char c = fgetc(sourcep);
      (void) fwrite(&c, 1, 1, destp);
    }
  }
  (void) fclose(destp);
  (void) fclose(sourcep);
}

int usage() {
      printf("Usage: %s <input_file> <page_size> <dest_directory> [columns]\n", __FILE__);
      printf("Generates <columns> PGM files where 1 pixel represent the value of one byte in the dump\n");
      return 1;
}
 
int main(int argc, char **argv) {
  struct stat st;
  long size;
  long page;
  long offset = 0;
  int columns = 8;

  if (argc == 1 || (strncmp(argv[1], "--help", 6)==0) || (strncmp(argv[1], "-h", 6) == 0)) {
      return usage();
  }

  if (argc < 4) {
      return usage();
  }
  char *input_filename = argv[1];
  char *dest_dir = argv[3];

  stat(input_filename, &st);
  size = st.st_size;

  page = strtol(argv[2], NULL, 10);

  if (size % page != 0) {
      printf("%s is of size %ld, which is not a multiple of page size %ld\n", input_filename, size, page);
      return 1;
  }

  if (argc == 5) {
      columns = strtol(argv[4], NULL, 10);
  }

  const int dimx = page;
  const long pixel_by_pic = size / columns;
  const int dimy = pixel_by_pic / dimx;

  printf("I'll generate %d PGM files for file %s\n", columns, input_filename);

  char dest[1024];
  for (int i=0; i < columns; i++) {
      snprintf(dest, 1024,  "%s/%s_%d_%ld-%ld.pgm", dest_dir, input_filename, i, offset, offset+pixel_by_pic);
      convert(input_filename, dest, dimx, dimy, offset);
      offset += pixel_by_pic;
  }

  return 0;
}
