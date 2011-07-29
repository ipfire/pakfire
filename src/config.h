
/*
	This is just a small configuration file for the build time configuration
	of the satsolver module.
*/

//#define DEBUG


#define STRING_SIZE	2048

/*
	Load all required modules for the translation.
*/

#include <libintl.h>

#define TEXTDOMAIN	"pakfire"
#define _(x) gettext(x)
