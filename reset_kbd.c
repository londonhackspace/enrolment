/*
 * for some reason when the enrolment thing crashes
 * it leaves the keyboard in a non-working state
 * this fixes it.
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>                     
#include <errno.h>
#include <error.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/kd.h>

//#define		K_RAW		0x00
//#define		K_XLATE		0x01
//#define		K_MEDIUMRAW	0x02
//#define		K_UNICODE	0x03
//#define		K_OFF		0x04
//#define KDGKBMODE	0x4B44	/* gets current keyboard mode */
//#define KDSKBMODE	0x4B45	/* sets current keyboard mode */


int main(int argc, char **argv) {
  char *console = "/dev/console";
  int fd, mode;
  
  fd = open(console, O_RDWR);
  if (fd < 0) {
    error(EXIT_FAILURE, errno, "open");
  }
  
  if (ioctl(fd, KDGETMODE, &mode) == -1)
    error(EXIT_FAILURE, errno, "ioctl");

  if (mode == KD_GRAPHICS) {
    printf("Changing to text mode.\n");
    if (ioctl(fd, KDSETMODE, KD_TEXT) == -1)
      error(EXIT_FAILURE, errno, "ioctl");
  }
  
  if (ioctl(fd, KDGKBMODE, &mode) == -1)
    error(EXIT_FAILURE, errno, "ioctl");
    
  if (mode != K_UNICODE) {
    printf("Switching to unicode.\n");
    if (ioctl(fd, KDSKBMODE, K_UNICODE) == -1)
      error(EXIT_FAILURE, errno, "ioctl");
  }

  return 0;
}