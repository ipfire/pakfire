#ifndef H_RPMTAG
#define	H_RPMTAG

/** \ingroup header
 * \file rpmdb/rpmtag.h
 */

#include <rpmiotypes.h>
#include <rpmsw.h>

#ifdef __cplusplus
extern "C" {
#endif

/** \ingroup header
 */
typedef const char *	errmsg_t;

/** \ingroup header
 */
typedef /*@abstract@*/ /*@refcounted@*/ struct headerToken_s * Header;

/** \ingroup header
 * The basic types of data in tags from headers.
 */
enum rpmTagType_e {
    	/* RPM_NULL_TYPE =  0	- never been used. */
	/* RPM_CHAR_TYPE =  1	- never been used, same as RPM_UINT8_TYPE. */
    RPM_UINT8_TYPE		=  2,
    RPM_UINT16_TYPE		=  3,
    RPM_UINT32_TYPE		=  4,
    RPM_UINT64_TYPE		=  5,
    RPM_STRING_TYPE		=  6,
    RPM_BIN_TYPE		=  7,
    RPM_STRING_ARRAY_TYPE	=  8,
    RPM_I18NSTRING_TYPE		=  9
	/* RPM_ASN1_TYPE = 10	- never been used. */
	/* RPM_OPENPGP_TYPE= 11	- never been used. */
};
#define	RPM_MIN_TYPE		2
#define	RPM_MAX_TYPE		9
#define	RPM_MASK_TYPE		0x0000ffff

/** \ingroup header
 */
typedef enum rpmTagType_e rpmTagType;	/*!< tag data type. */

/** \ingroup header
 */
typedef union rpmDataType_u rpmTagData;	/*!< tag data. */

/** \ingroup header
 */
typedef rpmuint32_t rpmTagCount;	/*!< tag data element count. */

/** \ingroup header
 */
typedef struct _HE_s * HE_t;	/*!< tag container. */

/** \ingroup header
 */
/*@-typeuse -fielduse@*/
#if !defined(SWIG)
union rpmDataType_u {
/*@null@*/
    void * ptr;
    rpmuint8_t * ui8p;		/*!< RPM_UINT8_TYPE | RPM_CHAR_TYPE */
    rpmuint16_t * ui16p;	/*!< RPM_UINT16_TYPE */
    rpmuint32_t * ui32p;	/*!< RPM_UINT32_TYPE */
    rpmuint64_t * ui64p;	/*!< RPM_UINT64_TYPE */
/*@relnull@*/
    const char * str;		/*!< RPM_STRING_TYPE */
    unsigned char * blob;	/*!< RPM_BIN_TYPE */
    const char ** argv;		/*!< RPM_STRING_ARRAY_TYPE */
    HE_t he;
};
#endif
/*@=typeuse =fielduse@*/

/*@=typeuse =fielduse@*/
/** \ingroup header
 */
/*@-enummemuse -typeuse @*/
typedef enum rpmSubTagType_e {
    RPM_REGION_TYPE		= -10,
    RPM_BIN_ARRAY_TYPE		= -11,
    RPM_XREF_TYPE		= -12
} rpmSubTagType;
/*@=enummemuse =typeuse @*/

/** \ingroup header
 * Identify how to return the header data type.
 */
/*@-enummemuse -typeuse @*/
typedef enum rpmTagReturnType_e {
    RPM_ANY_RETURN_TYPE		= 0,
    RPM_SCALAR_RETURN_TYPE	= 0x00010000,
    RPM_ARRAY_RETURN_TYPE	= 0x00020000,
    RPM_MAPPING_RETURN_TYPE	= 0x00040000,
	/* 0x00080000 */
    RPM_PROBE_RETURN_TYPE	= 0x00100000,
    RPM_TREE_RETURN_TYPE	= 0x00200000,
    RPM_OPENPGP_RETURN_TYPE	= 0x00400000,
    RPM_X509_RETURN_TYPE	= 0x00800000,
    RPM_ASN1_RETURN_TYPE	= 0x01000000,
    RPM_OPAQUE_RETURN_TYPE	= 0x10000000,
    RPM_MASK_RETURN_TYPE	= 0xffff0000
} rpmTagReturnType;
/*@=enummemuse =typeuse @*/

/**
 * Header private tags.
 * @note General use tags should start at 1000 (RPM's tag space starts there).
 */
#define	HEADER_IMAGE		61
#define	HEADER_SIGNATURES	62
#define	HEADER_IMMUTABLE	63
#define	HEADER_REGIONS		64
#define HEADER_I18NTABLE	100
#define	HEADER_SIGBASE		256
#define	HEADER_TAGBASE		1000

/** \ingroup header
 */
typedef /*@abstract@*/ struct headerIterator_s * HeaderIterator;

/** \ingroup header
 */
typedef /*@abstract@*/ struct headerTagIndices_s * headerTagIndices;

/** \ingroup header
 */
typedef /*@abstract@*/ const struct headerSprintfExtension_s * headerSprintfExtension;

/**
 * Pseudo-tags used by the rpmdb and rpmgi iterator API's.
 */
#define	RPMDBI_PACKAGES		0	/* Installed package headers. */
#define	RPMDBI_DEPENDS		1	/* Dependency resolution cache. */
	/* (obsolete) RPMDBI_LABEL was 2 */
#define	RPMDBI_ADDED		3	/* Added package headers. */
#define	RPMDBI_REMOVED		4	/* Removed package headers. */
#define	RPMDBI_AVAILABLE	5	/* Available package headers. */
#define	RPMDBI_HDLIST		6	/* (rpmgi) Header list. */
#define	RPMDBI_ARGLIST		7	/* (rpmgi) Argument list. */
#define	RPMDBI_FTSWALK		8	/* (rpmgi) File tree  walk. */
#define	RPMDBI_SEQNO		9	/* Sequence numbers. */
#define	RPMDBI_BTREE		10	/* (development) Generic DB_BTREE. */
#define	RPMDBI_HASH		11	/* (development) Generic DB_HASH. */
#define	RPMDBI_QUEUE		12	/* (development) Generic DB_QUEUE. */
#define	RPMDBI_RECNO		13	/* (development) Generic DB_RECNO. */
#define	RPMDBI_REPACKAGES	14	/* Re-packaged package paths. */
#define	RPMDBI_REPOSITORY	15	/* Repository URI's. */

/** \ingroup header
 * Tags identify data in package headers.
 * @note tags should not have value 0!
 */
enum rpmTag_e {

    RPMTAG_HEADERIMAGE		= HEADER_IMAGE,		/*!< internal Current image. */
    RPMTAG_HEADERSIGNATURES	= HEADER_SIGNATURES,	/*!< internal Signatures. */
    RPMTAG_HEADERIMMUTABLE	= HEADER_IMMUTABLE,	/*!< x Original image. */
/*@-enummemuse@*/
    RPMTAG_HEADERREGIONS	= HEADER_REGIONS,	/*!< internal Regions. */

    RPMTAG_HEADERI18NTABLE	= HEADER_I18NTABLE, /*!< s[] I18N string locales. */
/*@=enummemuse@*/

/* Retrofit (and uniqify) signature tags for use by tagName() and rpmQuery. */
/* the md5 sum was broken *twice* on big endian machines */
/* XXX 2nd underscore prevents tagTable generation */
    RPMTAG_SIG_BASE		= HEADER_SIGBASE,
    RPMTAG_SIGSIZE		= RPMTAG_SIG_BASE+1,	/* i */
    RPMTAG_SIGLEMD5_1		= RPMTAG_SIG_BASE+2,	/* internal - obsolete */
    RPMTAG_SIGPGP		= RPMTAG_SIG_BASE+3,	/* x */
    RPMTAG_SIGLEMD5_2		= RPMTAG_SIG_BASE+4,	/* x internal - obsolete */
    RPMTAG_SIGMD5	        = RPMTAG_SIG_BASE+5,	/* x */
#define	RPMTAG_PKGID	RPMTAG_SIGMD5			/* x */
    RPMTAG_SIGGPG	        = RPMTAG_SIG_BASE+6,	/* x */
    RPMTAG_SIGPGP5	        = RPMTAG_SIG_BASE+7,	/* internal - obsolete */

    RPMTAG_BADSHA1_1		= RPMTAG_SIG_BASE+8,	/* internal - obsolete */
    RPMTAG_BADSHA1_2		= RPMTAG_SIG_BASE+9,	/* internal - obsolete */
    RPMTAG_PUBKEYS		= RPMTAG_SIG_BASE+10,	/* s[] */
    RPMTAG_DSAHEADER		= RPMTAG_SIG_BASE+11,	/* x */
    RPMTAG_RSAHEADER		= RPMTAG_SIG_BASE+12,	/* x */
    RPMTAG_SHA1HEADER		= RPMTAG_SIG_BASE+13,	/* s */
#define	RPMTAG_HDRID	RPMTAG_SHA1HEADER	/* s */

    RPMTAG_NAME  		= 1000,	/* s */
#define	RPMTAG_N	RPMTAG_NAME	/* s */
    RPMTAG_VERSION		= 1001,	/* s */
#define	RPMTAG_V	RPMTAG_VERSION	/* s */
    RPMTAG_RELEASE		= 1002,	/* s */
#define	RPMTAG_R	RPMTAG_RELEASE	/* s */
    RPMTAG_EPOCH   		= 1003,	/* i */
#define	RPMTAG_E	RPMTAG_EPOCH	/* i */
    RPMTAG_SUMMARY		= 1004,	/* s{} */
    RPMTAG_DESCRIPTION		= 1005,	/* s{} */
    RPMTAG_BUILDTIME		= 1006,	/* i */
    RPMTAG_BUILDHOST		= 1007,	/* s */
    RPMTAG_INSTALLTIME		= 1008,	/* i[] */
    RPMTAG_SIZE			= 1009,	/* i */
    RPMTAG_DISTRIBUTION		= 1010,	/* s */
    RPMTAG_VENDOR		= 1011,	/* s */
    RPMTAG_GIF			= 1012,	/* x */
    RPMTAG_XPM			= 1013,	/* x */
    RPMTAG_LICENSE		= 1014,	/* s */
    RPMTAG_PACKAGER		= 1015,	/* s */
    RPMTAG_GROUP		= 1016,	/* s{} */
/*@-enummemuse@*/
    RPMTAG_CHANGELOG		= 1017, /* s[] internal */
/*@=enummemuse@*/
    RPMTAG_SOURCE		= 1018,	/* s[] */
    RPMTAG_PATCH		= 1019,	/* s[] */
    RPMTAG_URL			= 1020,	/* s */
    RPMTAG_OS			= 1021,	/* s legacy used int */
    RPMTAG_ARCH			= 1022,	/* s legacy used int */
    RPMTAG_PREIN		= 1023,	/* s */
    RPMTAG_POSTIN		= 1024,	/* s */
    RPMTAG_PREUN		= 1025,	/* s */
    RPMTAG_POSTUN		= 1026,	/* s */
    RPMTAG_OLDFILENAMES		= 1027, /* s[] obsolete */
    RPMTAG_FILESIZES		= 1028,	/* i[] */
    RPMTAG_FILESTATES		= 1029, /* c[] */
    RPMTAG_FILEMODES		= 1030,	/* h[] */
    RPMTAG_FILEUIDS		= 1031, /* i[] internal */
    RPMTAG_FILEGIDS		= 1032, /* i[] internal */
    RPMTAG_FILERDEVS		= 1033,	/* h[] */
    RPMTAG_FILEMTIMES		= 1034, /* i[] */
    RPMTAG_FILEDIGESTS		= 1035,	/* s[] */
#define RPMTAG_FILEMD5S	RPMTAG_FILEDIGESTS /* s[] */
    RPMTAG_FILELINKTOS		= 1036,	/* s[] */
    RPMTAG_FILEFLAGS		= 1037,	/* i[] */
/*@-enummemuse@*/
    RPMTAG_ROOT			= 1038, /* internal - obsolete */
/*@=enummemuse@*/
    RPMTAG_FILEUSERNAME		= 1039,	/* s[] */
    RPMTAG_FILEGROUPNAME	= 1040,	/* s[] */
/*@-enummemuse@*/
    RPMTAG_EXCLUDE		= 1041, /* internal - obsolete */
    RPMTAG_EXCLUSIVE		= 1042, /* internal - obsolete */
/*@=enummemuse@*/
    RPMTAG_ICON			= 1043, /* x */
    RPMTAG_SOURCERPM		= 1044,	/* s */
    RPMTAG_FILEVERIFYFLAGS	= 1045,	/* i[] */
    RPMTAG_ARCHIVESIZE		= 1046,	/* i */
    RPMTAG_PROVIDENAME		= 1047,	/* s[] */
#define	RPMTAG_PROVIDES RPMTAG_PROVIDENAME	/* s[] */
#define	RPMTAG_P	RPMTAG_PROVIDENAME	/* s[] */
    RPMTAG_REQUIREFLAGS		= 1048,	/* i[] */
    RPMTAG_REQUIRENAME		= 1049,	/* s[] */
#define	RPMTAG_REQUIRES RPMTAG_REQUIRENAME	/* s[] */
    RPMTAG_REQUIREVERSION	= 1050,	/* s[] */
    RPMTAG_NOSOURCE		= 1051, /* i internal */
    RPMTAG_NOPATCH		= 1052, /* i internal */
    RPMTAG_CONFLICTFLAGS	= 1053, /* i[] */
    RPMTAG_CONFLICTNAME		= 1054,	/* s[] */
#define	RPMTAG_CONFLICTS RPMTAG_CONFLICTNAME	/* s[] */
#define	RPMTAG_C	RPMTAG_CONFLICTNAME	/* s[] */
    RPMTAG_CONFLICTVERSION	= 1055,	/* s[] */
    RPMTAG_DEFAULTPREFIX	= 1056, /* s internal - deprecated */
    RPMTAG_BUILDROOT		= 1057, /* s internal */
    RPMTAG_INSTALLPREFIX	= 1058, /* s internal - deprecated */
    RPMTAG_EXCLUDEARCH		= 1059, /* s[] */
    RPMTAG_EXCLUDEOS		= 1060, /* s[] */
    RPMTAG_EXCLUSIVEARCH	= 1061, /* s[] */
    RPMTAG_EXCLUSIVEOS		= 1062, /* s[] */
    RPMTAG_AUTOREQPROV		= 1063, /* s internal */
    RPMTAG_RPMVERSION		= 1064,	/* s */
    RPMTAG_TRIGGERSCRIPTS	= 1065,	/* s[] */
    RPMTAG_TRIGGERNAME		= 1066,	/* s[] */
    RPMTAG_TRIGGERVERSION	= 1067,	/* s[] */
    RPMTAG_TRIGGERFLAGS		= 1068,	/* i[] */
    RPMTAG_TRIGGERINDEX		= 1069,	/* i[] */
    RPMTAG_VERIFYSCRIPT		= 1079,	/* s */
    RPMTAG_CHANGELOGTIME	= 1080,	/* i[] */
    RPMTAG_CHANGELOGNAME	= 1081,	/* s[] */
    RPMTAG_CHANGELOGTEXT	= 1082,	/* s[] */
/*@-enummemuse@*/
    RPMTAG_BROKENMD5		= 1083, /* internal - obsolete */
/*@=enummemuse@*/
    RPMTAG_PREREQ		= 1084, /* internal */
    RPMTAG_PREINPROG		= 1085,	/* s */
    RPMTAG_POSTINPROG		= 1086,	/* s */
    RPMTAG_PREUNPROG		= 1087,	/* s */
    RPMTAG_POSTUNPROG		= 1088,	/* s */
    RPMTAG_BUILDARCHS		= 1089, /* s[] */
    RPMTAG_OBSOLETENAME		= 1090,	/* s[] */
#define	RPMTAG_OBSOLETES RPMTAG_OBSOLETENAME	/* s[] */
#define	RPMTAG_O	RPMTAG_OBSOLETENAME	/* s[] */
    RPMTAG_VERIFYSCRIPTPROG	= 1091,	/* s */
    RPMTAG_TRIGGERSCRIPTPROG	= 1092,	/* s[] */
    RPMTAG_DOCDIR		= 1093, /* internal */
    RPMTAG_COOKIE		= 1094,	/* s */
    RPMTAG_FILEDEVICES		= 1095,	/* i[] */
    RPMTAG_FILEINODES		= 1096,	/* i[] */
    RPMTAG_FILELANGS		= 1097,	/* s[] */
    RPMTAG_PREFIXES		= 1098,	/* s[] */
    RPMTAG_INSTPREFIXES		= 1099,	/* s[] */
    RPMTAG_TRIGGERIN		= 1100, /* internal */
    RPMTAG_TRIGGERUN		= 1101, /* internal */
    RPMTAG_TRIGGERPOSTUN	= 1102, /* internal */
    RPMTAG_AUTOREQ		= 1103, /* internal */
    RPMTAG_AUTOPROV		= 1104, /* internal */
/*@-enummemuse@*/
    RPMTAG_CAPABILITY		= 1105, /* i legacy - obsolete */
/*@=enummemuse@*/
    RPMTAG_SOURCEPACKAGE	= 1106, /* i legacy - obsolete */
/*@-enummemuse@*/
    RPMTAG_OLDORIGFILENAMES	= 1107, /* internal - obsolete */
/*@=enummemuse@*/
    RPMTAG_BUILDPREREQ		= 1108, /* internal */
    RPMTAG_BUILDREQUIRES	= 1109, /* internal */
    RPMTAG_BUILDCONFLICTS	= 1110, /* internal */
/*@-enummemuse@*/
    RPMTAG_BUILDMACROS		= 1111, /* s[] srpms only */
/*@=enummemuse@*/
    RPMTAG_PROVIDEFLAGS		= 1112,	/* i[] */
    RPMTAG_PROVIDEVERSION	= 1113,	/* s[] */
    RPMTAG_OBSOLETEFLAGS	= 1114,	/* i[] */
    RPMTAG_OBSOLETEVERSION	= 1115,	/* s[] */
    RPMTAG_DIRINDEXES		= 1116,	/* i[] */
    RPMTAG_BASENAMES		= 1117,	/* s[] */
    RPMTAG_DIRNAMES		= 1118,	/* s[] */
    RPMTAG_ORIGDIRINDEXES	= 1119, /* i[] relocation */
    RPMTAG_ORIGBASENAMES	= 1120, /* s[] relocation */
    RPMTAG_ORIGDIRNAMES		= 1121, /* s[] relocation */
    RPMTAG_OPTFLAGS		= 1122,	/* s */
    RPMTAG_DISTURL		= 1123,	/* s */
    RPMTAG_PAYLOADFORMAT	= 1124,	/* s */
    RPMTAG_PAYLOADCOMPRESSOR	= 1125,	/* s */
    RPMTAG_PAYLOADFLAGS		= 1126,	/* s */
    RPMTAG_INSTALLCOLOR		= 1127, /* i transaction color when installed */
    RPMTAG_INSTALLTID		= 1128,	/* i[] */
    RPMTAG_REMOVETID		= 1129,	/* i[] */
/*@-enummemuse@*/
    RPMTAG_SHA1RHN		= 1130, /* internal - obsolete */
/*@=enummemuse@*/
    RPMTAG_RHNPLATFORM		= 1131,	/* s deprecated */
    RPMTAG_PLATFORM		= 1132,	/* s */
    RPMTAG_PATCHESNAME		= 1133, /* s[] deprecated placeholder (SuSE) */
    RPMTAG_PATCHESFLAGS		= 1134, /* i[] deprecated placeholder (SuSE) */
    RPMTAG_PATCHESVERSION	= 1135, /* s[] deprecated placeholder (SuSE) */
    RPMTAG_CACHECTIME		= 1136,	/* i rpmcache(8) only */
    RPMTAG_CACHEPKGPATH		= 1137,	/* s rpmcache(8) only */
    RPMTAG_CACHEPKGSIZE		= 1138,	/* i rpmcache(8) only */
    RPMTAG_CACHEPKGMTIME	= 1139,	/* i rpmcache(8) only */
    RPMTAG_FILECOLORS		= 1140,	/* i[] */
    RPMTAG_FILECLASS		= 1141,	/* i[] */
    RPMTAG_CLASSDICT		= 1142,	/* s[] */
    RPMTAG_FILEDEPENDSX		= 1143,	/* i[] */
    RPMTAG_FILEDEPENDSN		= 1144,	/* i[] */
    RPMTAG_DEPENDSDICT		= 1145,	/* i[] */
    RPMTAG_SOURCEPKGID		= 1146,	/* x */
    RPMTAG_FILECONTEXTS		= 1147,	/* s[] */
    RPMTAG_FSCONTEXTS		= 1148,	/* s[] extension */
    RPMTAG_RECONTEXTS		= 1149,	/* s[] extension */
    RPMTAG_POLICIES		= 1150,	/* s[] selinux *.te policy file. */
    RPMTAG_PRETRANS		= 1151,	/* s */
    RPMTAG_POSTTRANS		= 1152,	/* s */
    RPMTAG_PRETRANSPROG		= 1153,	/* s */
    RPMTAG_POSTTRANSPROG	= 1154,	/* s */
    RPMTAG_DISTTAG		= 1155,	/* s */
    RPMTAG_SUGGESTSNAME		= 1156,	/* s[] extension */
#define	RPMTAG_SUGGESTS RPMTAG_SUGGESTSNAME	/* s[] */
    RPMTAG_SUGGESTSVERSION	= 1157,	/* s[] extension */
    RPMTAG_SUGGESTSFLAGS	= 1158,	/* i[] extension */
    RPMTAG_ENHANCESNAME		= 1159,	/* s[] extension placeholder */
#define	RPMTAG_ENHANCES RPMTAG_ENHANCESNAME	/* s[] */
    RPMTAG_ENHANCESVERSION	= 1160,	/* s[] extension placeholder */
    RPMTAG_ENHANCESFLAGS	= 1161,	/* i[] extension placeholder */
    RPMTAG_PRIORITY		= 1162, /* i[] extension placeholder */
    RPMTAG_CVSID		= 1163, /* s */
#define	RPMTAG_SVNID	RPMTAG_CVSID	/* s */
    RPMTAG_BLINKPKGID		= 1164, /* s[] */
    RPMTAG_BLINKHDRID		= 1165, /* s[] */
    RPMTAG_BLINKNEVRA		= 1166, /* s[] */
    RPMTAG_FLINKPKGID		= 1167, /* s[] */
    RPMTAG_FLINKHDRID		= 1168, /* s[] */
    RPMTAG_FLINKNEVRA		= 1169, /* s[] */
    RPMTAG_PACKAGEORIGIN	= 1170, /* s */
    RPMTAG_TRIGGERPREIN		= 1171, /* internal */
    RPMTAG_BUILDSUGGESTS	= 1172, /* internal */
    RPMTAG_BUILDENHANCES	= 1173, /* internal */
    RPMTAG_SCRIPTSTATES		= 1174, /* i[] scriptlet exit codes */
    RPMTAG_SCRIPTMETRICS	= 1175, /* i[] scriptlet execution times */
    RPMTAG_BUILDCPUCLOCK	= 1176, /* i */
    RPMTAG_FILEDIGESTALGOS	= 1177, /* i[] */
    RPMTAG_VARIANTS		= 1178, /* s[] */
    RPMTAG_XMAJOR		= 1179, /* i */
    RPMTAG_XMINOR		= 1180, /* i */
    RPMTAG_REPOTAG		= 1181,	/* s */
    RPMTAG_KEYWORDS		= 1182,	/* s[] */
    RPMTAG_BUILDPLATFORMS	= 1183,	/* s[] */
    RPMTAG_PACKAGECOLOR		= 1184, /* i */
    RPMTAG_PACKAGEPREFCOLOR	= 1185, /* i (unimplemented) */
    RPMTAG_XATTRSDICT		= 1186, /* s[] (unimplemented) */
    RPMTAG_FILEXATTRSX		= 1187, /* i[] (unimplemented) */
    RPMTAG_DEPATTRSDICT		= 1188, /* s[] (unimplemented) */
    RPMTAG_CONFLICTATTRSX	= 1189, /* i[] (unimplemented) */
    RPMTAG_OBSOLETEATTRSX	= 1190, /* i[] (unimplemented) */
    RPMTAG_PROVIDEATTRSX	= 1191, /* i[] (unimplemented) */
    RPMTAG_REQUIREATTRSX	= 1192, /* i[] (unimplemented) */
    RPMTAG_BUILDPROVIDES	= 1193, /* internal */
    RPMTAG_BUILDOBSOLETES	= 1194, /* internal */
    RPMTAG_DBINSTANCE		= 1195, /* i */
    RPMTAG_NVRA			= 1196, /* s */
    RPMTAG_FILEPATHS		= 1197, /* s[] */
    RPMTAG_ORIGPATHS		= 1198, /* s[] */
    RPMTAG_RPMLIBVERSION	= 1199, /* i */
    RPMTAG_RPMLIBTIMESTAMP	= 1200, /* i */
    RPMTAG_RPMLIBVENDOR		= 1201, /* i */
    RPMTAG_CLASS		= 1202, /* s arbitrary */
    RPMTAG_TRACK		= 1203, /* s internal arbitrary */
    RPMTAG_TRACKPROG		= 1204, /* s internal arbitrary */
    RPMTAG_SANITYCHECK		= 1205, /* s */
    RPMTAG_SANITYCHECKPROG	= 1206, /* s */
    RPMTAG_FILESTAT		= 1207, /* s[] stat(2) from metadata extension*/
    RPMTAG_STAT			= 1208, /* s[] stat(2) from disk extension */
    RPMTAG_ORIGINTID		= 1209,	/* i[] */
    RPMTAG_ORIGINTIME		= 1210,	/* i[] */
    RPMTAG_HEADERSTARTOFF	= 1211,	/* l */
    RPMTAG_HEADERENDOFF		= 1212,	/* l */
    RPMTAG_PACKAGETIME		= 1213,	/* l */
    RPMTAG_PACKAGESIZE		= 1214,	/* l */
    RPMTAG_PACKAGEDIGEST	= 1215,	/* s */
    RPMTAG_PACKAGESTAT		= 1216,	/* x */
    RPMTAG_PACKAGEBASEURL	= 1217,	/* s */
    RPMTAG_DISTEPOCH		= 1218, /* s */
#define	RPMTAG_D RPMTAG_DISTEPOCH	/* s */

    RPMTAG_CONFLICTYAMLENTRY	= 1219, /* s[] */
    RPMTAG_OBSOLETEYAMLENTRY	= 1220, /* s[] */
    RPMTAG_PROVIDEYAMLENTRY	= 1221, /* s[] */
    RPMTAG_REQUIREYAMLENTRY	= 1222, /* s[] */

    RPMTAG_FILEDIGESTALGO	= 5011, /* i file checksum algorithm */
    RPMTAG_BUGURL		= 5012, /* s */

/*@-enummemuse@*/
    RPMTAG_FIRSTFREE_TAG,	/*!< internal */
/*@=enummemuse@*/

    RPMTAG_PACKAGETRANSFLAGS	= 0x4efaafd9, /* s[] arbitrary */
    RPMTAG_PACKAGEDEPFLAGS	= 0x748a8314, /* s[] arbitrary */

    RPMTAG_BUILDPREPPROG	= 0x4ba37c9e, /* s[] arbitrary */
    RPMTAG_BUILDPREP		= 0x799c0b4d, /* s[] arbitrary */
    RPMTAG_BUILDBUILDPROG	= 0x6fb46014, /* s[] arbitrary */
    RPMTAG_BUILDBUILD		= 0x5bae1a5a, /* s[] arbitrary */
    RPMTAG_BUILDINSTALLPROG	= 0x70d4ab6f, /* s[] arbitrary */
    RPMTAG_BUILDINSTALL		= 0x567f5983, /* s[] arbitrary */
    RPMTAG_BUILDCHECKPROG	= 0x488a60ce, /* s[] arbitrary */
    RPMTAG_BUILDCHECK		= 0x7f3b97b5, /* s[] arbitrary */
    RPMTAG_BUILDCLEANPROG	= 0x42c93d41, /* s[] arbitrary */
    RPMTAG_BUILDCLEAN		= 0x566042bf, /* s[] arbitrary */

    RPMTAG_LASTARBITRARY_TAG	= 0x80000000  /*!< internal */
};

#define	RPMTAG_EXTERNAL_TAG		1000000

/** \ingroup signature
 * Tags found in signature header from package.
 */
enum rpmSigTag_e {
    RPMSIGTAG_SIZE	= 1000,	/*!< internal Header+Payload size in bytes. */
    RPMSIGTAG_LEMD5_1	= 1001,	/*!< internal Broken MD5, take 1 @deprecated legacy. */
    RPMSIGTAG_PGP	= 1002,	/*!< internal PGP 2.6.3 signature. */
    RPMSIGTAG_LEMD5_2	= 1003,	/*!< internal Broken MD5, take 2 @deprecated legacy. */
    RPMSIGTAG_MD5	= 1004,	/*!< internal MD5 signature. */
    RPMSIGTAG_GPG	= 1005, /*!< internal GnuPG signature. */
    RPMSIGTAG_PGP5	= 1006,	/*!< internal PGP5 signature @deprecated legacy. */
    RPMSIGTAG_PAYLOADSIZE = 1007,/*!< internal uncompressed payload size in bytes. */
    RPMSIGTAG_BADSHA1_1	= RPMTAG_BADSHA1_1,	/*!< internal Broken SHA1, take 1. */
    RPMSIGTAG_BADSHA1_2	= RPMTAG_BADSHA1_2,	/*!< internal Broken SHA1, take 2. */
    RPMSIGTAG_SHA1	= RPMTAG_SHA1HEADER,	/*!< internal sha1 header digest. */
    RPMSIGTAG_DSA	= RPMTAG_DSAHEADER,	/*!< internal DSA header signature. */
    RPMSIGTAG_RSA	= RPMTAG_RSAHEADER,	/*!< internal RSA header signature. */
    RPMSIGTAG_PADDING	= 0x3fffffff		/*!< signature header padding */
};

/** \ingroup header
 */
typedef enum rpmTag_e rpmTag;

/** \ingroup header
 */
typedef enum rpmSigTag_e rpmSigTag;

/** \ingroup header
 */
/*@-typeuse -fielduse@*/
#if !defined(SWIG)
struct _HE_s {
    rpmTag tag;
    rpmTagType t;
/*@owned@*/ /*@null@*/
    rpmTagData p;
    rpmTagCount c;
    int ix;
    unsigned int freeData	: 1;
    unsigned int avail		: 1;
    unsigned int append		: 1;
};
#endif

/**
 */
typedef struct _HE_s HE_s;

/** \ingroup rpmdb
 */
typedef struct tagStore_s * tagStore_t;

/**
 */
typedef /*@abstract@*/ const struct headerTagTableEntry_s * headerTagTableEntry;

#if defined(_RPMTAG_INTERNAL)
/**
 */
/** \ingroup header
 * Associate tag names with numeric values.
 */
#if !defined(SWIG)
struct headerTagTableEntry_s {
/*@observer@*/ /*@relnull@*/
    const char * name;		/*!< Tag name. */
    rpmTag val;			/*!< Tag numeric value. */
    rpmTagType type;		/*!< Tag type. */
};
#endif

/**
 */ 
struct tagStore_s {
/*@only@*/
    const char * str;           /*!< Tag string (might be arbitrary). */
    rpmTag tag;                 /*!< Tag number. */
    rpmiob iob;			/*!< Tag contents. */
};  
#endif	/* _RPMTAG_INTERNAL */

/**
 * Automatically generated table of tag name/value pairs.
 */
/*@-redecl@*/
/*@observer@*/ /*@unchecked@*/
extern headerTagTableEntry rpmTagTable;
/*@=redecl@*/

/**
 * Number of entries in rpmTagTable.
 */
/*@-redecl@*/
/*@unchecked@*/
extern int rpmTagTableSize;

/*@unchecked@*/
extern headerTagIndices rpmTags;
/*@=redecl@*/

#if defined(_RPMTAG_INTERNAL)
/**
 */
#if !defined(SWIG)
struct headerTagIndices_s {
/*@relnull@*/
    int (*loadIndex) (headerTagTableEntry ** ipp, size_t * np,
                int (*cmp) (const void * avp, const void * bvp))
        /*@ modifies *ipp, *np */;	/*!< Load sorted tag index. */
/*@relnull@*/
    headerTagTableEntry * byName;	/*!< rpmTag's sorted by name. */
    size_t byNameSize;			/*!< No. of entries. */
    int (*byNameCmp) (const void * avp, const void * bvp)
        /*@*/;				/*!< Compare entries by name. */
    rpmTag (*tagValue) (const char * name)
	/*@*/;				/*!< Return value from name. */
/*@relnull@*/
    headerTagTableEntry * byValue;	/*!< rpmTag's sorted by value. */
    size_t byValueSize;			/*!< No. of entries. */
    int (*byValueCmp) (const void * avp, const void * bvp)
        /*@*/;				/*!< Compare entries by value. */
    const char * (*tagName) (rpmTag value)
	/*@*/;				/*!< Return name from value. */
    rpmTag (*tagType) (rpmTag value)
	/*@*/;				/*!< Return type from value. */
    size_t nameBufLen;			/*!< No. bytes allocated for nameBuf. */
/*@relnull@*/
    const char ** aTags;		/*!< Arbitrary tags array (ARGV_t) */
/*@owned@*/ /*@null@*/
    char * nameBuf;			/* Name buffer. */
/*@only@*/
    char * (*tagCanonicalize) (const char * s)
	/*@*/;				/*!< Canonicalize arbitrary string. */
    rpmTag (*tagGenerate) (const char * s)
	/*@*/;				/*!< Generate tag from string. */
};
#endif
#endif	/* _RPMTAG_INTERNAL */

/**
 * Return tag name from value.
 * @param tag		tag value
 * @return		tag name, "(unknown)" on not found
 */
/*@observer@*/
const char * tagName(rpmTag tag)
	/*@*/;

/**
 * Return tag data type from value.
 * @todo Return rpmTagType-like, not unsigned int. There's no clear typedef yet.
 * @param tag		tag value
 * @return		tag data type, 0 on not found.
 */
unsigned int tagType(rpmTag tag)
	/*@*/;

/**
 * Return tag value from name.
 * @param tagstr	name of tag
 * @return		tag value, 0xffffffff on not found
 */
rpmTag tagValue(const char * tagstr)
	/*@*/;

/**
 * Canonicalize a rpmTag string.
 * @param s		string
 * @return		canonicalized string
 */
/*@only@*/
char * tagCanonicalize(const char * s)
	/*@*/;

/**
 * Generate a tag from arbitrary string.
 * @param s		string
 * @return		generated tag value
 */
rpmTag tagGenerate(const char * s)
	/*@*/;

/**
 * Free memory in header tag indices.
 * @param _rpmTags	header tag indices (NULL uses rpmTags)
 */
void tagClean(/*@null@*/ headerTagIndices _rpmTags)
	/*@globals rpmTags @*/
	/*@modifies _rpmTags, rpmTags @*/;

/**
 * Destroy tagStore array.
 * @param dbiTags	dbi tag storage
 * @param dbiNTags	no. of dbi tags
 * @return		NULL always
 */
/*@null@*/
tagStore_t tagStoreFree(/*@only@*//*@null@*/tagStore_t dbiTags, size_t dbiNTags)
	/*@modifies dbiTags @*/;

#if defined(_RPMTAG_INTERNAL)
/** \ingroup header
 */
typedef enum headerSprintfExtensionType_e {
    HEADER_EXT_LAST = 0,	/*!< End of extension chain. */
    HEADER_EXT_FORMAT,		/*!< headerTagFormatFunction() extension */
    HEADER_EXT_MORE,		/*!< Chain to next table. */
    HEADER_EXT_TAG		/*!< headerTagTagFunction() extension */
} headerSprintfExtensionType;

/** \ingroup header
 * HEADER_EXT_TAG format function prototype.
 *
 * @param he		tag container
 * @param av		parameter array (or NULL)
 * @return		formatted string
 */
typedef /*only@*/ char * (*headerTagFormatFunction) (HE_t he, /*@null@*/ const char ** av)
	/*@modifies he @*/;

/** \ingroup header
 * HEADER_EXT_FORMAT format function prototype.
 * This is allowed to fail, which indicates the tag doesn't exist.
 *
 * @param h		header
 * @retval he		tag container
 * @return		0 on success
 */
typedef int (*headerTagTagFunction) (Header h, HE_t he)
	/*@modifies he @*/;

/** \ingroup header
 * Define header tag output formats.
 */
#if !defined(SWIG)
struct headerSprintfExtension_s {
    headerSprintfExtensionType type;		/*!< Type of extension. */
/*@observer@*/ /*@null@*/
    const char * name;				/*!< Name of extension. */
    union {
/*@observer@*/ /*@null@*/
	void * generic;				/*!< Private extension. */
	headerTagFormatFunction fmtFunction; /*!< HEADER_EXT_TAG extension. */
	headerTagTagFunction tagFunction; /*!< HEADER_EXT_FORMAT extension. */
	headerSprintfExtension * more;	/*!< Chained table extension. */
    } u;
};
#endif
#endif	/* _RPMTAG_INTERNAL */

/** \ingroup header
 * Supported default header tag output formats.
 */
/*@unchecked@*/ /*@observer@*/
extern headerSprintfExtension headerDefaultFormats;

/** \ingroup header
 * Supported default header extension/tag output formats.
 */
/*@unchecked@*/ /*@observer@*/
extern headerSprintfExtension headerCompoundFormats;

/**
 * Display list of tags that can be used in --queryformat.
 * @param fp		file handle to use for display (NULL uses stdout)
 * @param _rpmTagTable	rpm tag table (NULL uses rpmTagTable)
 * @param _rpmHeaderFormats	rpm tag extensions & formats (NULL uses headerCompoundFormats)
 */
void rpmDisplayQueryTags(/*@null@*/ FILE * fp,
		/*@null@*/ headerTagTableEntry _rpmTagTable,
		/*@null@*/ headerSprintfExtension _rpmHeaderFormats)
	/*@globals fileSystem, internalState @*/
	/*@modifies *fp, fileSystem, internalState @*/;

/** \ingroup header
 * Return formatted output string from header tags.
 * The returned string must be free()d.
 *
 * @param h		header
 * @param fmt		format to use
 * @param tags		array of tag name/value/type triples (NULL uses default)
 * @param exts		formatting extensions chained table (NULL uses default)
 * @retval errmsg	error message (if any)
 * @return		formatted output string (malloc'ed)
 */
/*@only@*/ /*@null@*/
char * headerSprintf(Header h, const char * fmt,
		/*@null@*/ headerTagTableEntry tags,
		/*@null@*/ headerSprintfExtension exts,
		/*@null@*/ /*@out@*/ errmsg_t * errmsg)
	/*@globals headerCompoundFormats, fileSystem, internalState @*/
	/*@modifies h, *errmsg, fileSystem, internalState @*/;

/** \ingroup header
 * Retrieve extension or tag value from a header.
 *
 * @param h		header
 * @param he		tag container
 * @param flags		tag retrieval flags
 * @return		1 on success, 0 on failure
 */
int headerGet(Header h, HE_t he, unsigned int flags)
	/*@globals internalState @*/
	/*@modifies he, internalState @*/;
#define	HEADERGET_NOEXTENSION	(1 << 0) /*!< Extension search disabler. */
#define	HEADERGET_NOI18NSTRING	(1 << 1) /*!< Return i18n strings as argv. */

/** \ingroup header
 * Add or append tag container to header.
 *
 * @param h		header
 * @param he		tag container
 * @param flags		(unused)
 * @return		1 on success, 0 on failure
 */
/*@mayexit@*/
int headerPut(Header h, HE_t he, /*@unused@*/ unsigned int flags)
	/*@modifies h @*/;

/** \ingroup header
 * Remove tag container from header.
 *
 * @param h		header
 * @param he		tag container
 * @param flags		(unused)
 * @return		1 on success, 0 on failure
 */
/*@mayexit@*/
int headerDel(Header h, HE_t he, /*@unused@*/ unsigned int flags)
	/*@modifies h @*/;

/** \ingroup header
 * Modify tag container in header.
 * If there are multiple entries with this tag, the first one gets replaced.
 * @param h		header
 * @param he		tag container
 * @param flags		(unused)
 * @return		1 on success, 0 on failure
 */
int headerMod(Header h, HE_t he, /*@unused@*/ unsigned int flags)
	/*@modifies h @*/;

/** \ingroup header
 * Destroy header tag container iterator.
 * @param hi		header tag container iterator
 * @return		NULL always
 */
/*@null@*/
HeaderIterator headerFini(/*@only@*/ HeaderIterator hi)
	/*@globals fileSystem @*/
	/*@modifies hi, fileSystem */;

/** \ingroup header
 * Create header tag iterator.
 * @param h		header
 * @return		header tag iterator
 */
HeaderIterator headerInit(Header h)
	/*@globals fileSystem @*/
	/*@modifies h, fileSystem */;

/** \ingroup header
 * Return next tag from header.
 * @param hi		header tag iterator
 * @param he		tag container
 * @param flags		(unused)
 * @return		1 on success, 0 on failure
 */
int headerNext(HeaderIterator hi, HE_t he, /*@unused@*/ unsigned int flags)
	/*@globals internalState @*/
	/*@modifies hi, he, internalState @*/;

/** \ingroup header
 * Reference a header instance.
 * @param h		header
 * @return		referenced header instance
 */
Header headerLink(Header h)
	/*@modifies h @*/;
#define headerLink(_h)        \
    ((Header)rpmioLinkPoolItem((rpmioItem)(_h), __FUNCTION__, __FILE__, __LINE__))

/** \ingroup header
 * Dereference a header instance.
 * @param h		header
 * @return		NULL on last dereference
 */
/*@null@*/
Header headerUnlink(/*@killref@*/ /*@null@*/ Header h)
	/*@modifies h @*/;
#define headerUnlink(_h)        \
    ((Header)rpmioUnlinkPoolItem((rpmioItem)(_h), __FUNCTION__, __FILE__, __LINE__))

/** \ingroup header
 * Dereference a header instance.
 * @param h		header
 * @return		NULL on last dereference
 */
/*@null@*/
Header headerFree(/*@killref@*/ /*@null@*/ Header h)
	/*@modifies h @*/;
#define headerFree(_h)        \
    ((Header)rpmioFreePoolItem((rpmioItem)(_h), __FUNCTION__, __FILE__, __LINE__))

/** \ingroup header
 * Create new (empty) header instance.
 * @return		header
 */
Header headerNew(void)
	/*@globals fileSystem @*/
	/*@modifies fileSystem @*/;

/** \ingroup header
 * Return size of on-disk header representation in bytes.
 * @param h		header
 * @return		size of on-disk header
 */
size_t headerSizeof(/*@null@*/ Header h)
	/*@modifies h @*/;

/** \ingroup header
 * headerUnload.
 * @param h		header
 * @retval *lenp	no. bytes in unloaded header blob
 * @return		unloaded header blob (NULL on error)
 */
/*@only@*/ /*@null@*/
void * headerUnload(Header h, /*@out@*/ /*@null@*/ size_t * lenp)
	/*@globals internalState @*/
	/*@modifies h, *lenp, internalState @*/;

/** \ingroup header
 * Convert header to on-disk representation, and then reload.
 * This is used to insure that all header data is in a single
 * contiguous memory allocation.
 * @param h		header (with pointers)
 * @param tag		region tag
 * @return		on-disk header (with offsets)
 */
/*@null@*/
Header headerReload(/*@only@*/ Header h, int tag)
	/*@globals fileSystem, internalState @*/
	/*@modifies h, fileSystem, internalState @*/;

/** \ingroup header
 * Duplicate a header.
 * @param h		header
 * @return		new header instance
 */
/*@null@*/
Header headerCopy(Header h)
	/*@globals fileSystem, internalState @*/
	/*@modifies h, fileSystem, internalState @*/;

/** \ingroup header
 * Convert header to in-memory representation.
 * @param uh		on-disk header blob (i.e. with offsets)
 * @return		header
 */
/*@null@*/
Header headerLoad(/*@kept@*/ void * uh)
	/*@globals fileSystem, internalState @*/
	/*@modifies uh, fileSystem, internalState @*/;

/** \ingroup header
 * Make a copy and convert header to in-memory representation.
 * @param uh		on-disk header blob (i.e. with offsets)
 * @return		header
 */
/*@null@*/
Header headerCopyLoad(const void * uh)
	/*@globals fileSystem, internalState @*/
	/*@modifies fileSystem, internalState @*/;

/** \ingroup header
 * Check if tag is in header.
 * @param h		header
 * @param tag		tag
 * @return		1 on success, 0 on failure
 */
int headerIsEntry(/*@null@*/ Header h, rpmTag tag)
	/*@*/;

/** \ingroup header
 * Add locale specific tag to header.
 * A NULL lang is interpreted as the C locale. Here are the rules:
 * \verbatim
 *	- If the tag isn't in the header, it's added with the passed string
 *	   as new value.
 *	- If the tag occurs multiple times in entry, which tag is affected
 *	   by the operation is undefined.
 *	- If the tag is in the header w/ this language, the entry is
 *	   *replaced* (like headerModifyEntry()).
 * \endverbatim
 * This function is intended to just "do the right thing". If you need
 * more fine grained control use headerAddEntry() and headerModifyEntry().
 *
 * @param h		header
 * @param tag		tag
 * @param string	tag value
 * @param lang		locale
 * @return		1 on success, 0 on failure
 */
int headerAddI18NString(Header h, rpmTag tag, const char * string,
		const char * lang)
	/*@modifies h @*/;

/** \ingroup header
 * Duplicate tag values from one header into another.
 * @param headerFrom	source header
 * @param headerTo	destination header
 * @param tagstocopy	array of tags that are copied
 */
void headerCopyTags(Header headerFrom, Header headerTo, rpmTag * tagstocopy)
	/*@globals internalState @*/
	/*@modifies headerTo, internalState @*/;

/** \ingroup header
 * Return header magic.
 * @param h		header
 * @param *magicp	magic array
 * @param *nmagicp	no. bytes of magic
 * @return		0 always
 */
int headerGetMagic(/*@null@*/ Header h, unsigned char **magicp, size_t *nmagicp)
	/*@modifies *magicp, *nmagicp @*/;

/** \ingroup header
 * Store header magic.
 * @param h		header
 * @param magic		magic array
 * @param nmagic	no. bytes of magic
 * @return		0 always
 */
int headerSetMagic(/*@null@*/ Header h, unsigned char * magic, size_t nmagic)
	/*@modifies h @*/;

/** \ingroup header
 * Return header origin (e.g path or URL).
 * @param h		header
 * @return		header origin
 */
/*@observer@*/ /*@null@*/
const char * headerGetOrigin(/*@null@*/ Header h)
	/*@*/;

/** \ingroup header
 * Store header origin (e.g path or URL).
 * @param h		header
 * @param origin	new header origin
 * @return		0 always
 */
int headerSetOrigin(/*@null@*/ Header h, const char * origin)
	/*@modifies h @*/;

/** \ingroup header
 * Return header parent identifier (e.g parent's NVRA).
 * @param h		header
 * @return		header parent
 */
/*@observer@*/ /*@null@*/
const char * headerGetParent(/*@null@*/ Header h)
	/*@*/;

/** \ingroup header
 * Store header parent (e.g parent's NVRA).
 * @param h		header
 * @param parent	new header parent
 * @return		0 always
 */
int headerSetParent(/*@null@*/ Header h, const char * parent)
	/*@modifies h @*/;

/** \ingroup header
 * Return header base URL (e.g path or URL).
 * @param h		header
 * @return		header origin
 */
/*@observer@*/ /*@null@*/
const char * headerGetBaseURL(/*@null@*/ Header h)
	/*@*/;

/** \ingroup header
 * Store header base URL (e.g path or URL).
 * @param h		header
 * @param baseurl	new header baseurl
 * @return		0 always
 */
int headerSetBaseURL(/*@null@*/ Header h, const char * baseurl)
	/*@modifies h @*/;

/** \ingroup header
 * Return header stat(2) buffer (of origin *.rpm file).
 * @param h		header
 * @return		header stat(2) buffer
 */
struct stat * headerGetStatbuf(/*@null@*/ Header h)
	/*@*/;

/** \ingroup header
 * Copy into header stat(2) buffer (of origin *.rpm file).
 * @param h		header
 * @param st		new header stat(2) buffer
 * @return		0 always
 */
int headerSetStatbuf(/*@null@*/ Header h, struct stat * st)
	/*@modifies h @*/;

/** \ingroup header
 * Return digest of origin *.rpm file.
 * @param h		header
 * @return		header digest
 */
/*@null@*/
const char * headerGetDigest(/*@null@*/ Header h)
	/*@*/;

/** \ingroup header
 * Store digest of origin *.rpm file.
 * @param h		header
 * @param st		new header digest
 * @return		0 always
 */
int headerSetDigest(/*@null@*/ Header h, const char * digest)
	/*@modifies h @*/;

/** \ingroup header
 * Return rpmdb pointer.
 * @param h		header
 * @return		rpmdb pointer
 */
/*@null@*/
void * headerGetRpmdb(/*@null@*/ Header h)
	/*@*/;

/** \ingroup header
 * Store rpmdb pointer.
 * @param h		header
 * @param rpmdb		new rpmdb pointer (or NULL to unset)
 * @return		NULL always
 */
/*@null@*/
void * headerSetRpmdb(/*@null@*/ Header h, /*@null@*/ void * rpmdb)
	/*@modifies h @*/;

/** \ingroup header
 * Return header instance (if from rpmdb).
 * @param h		header
 * @return		header instance
 */
uint32_t headerGetInstance(/*@null@*/ Header h)
	/*@*/;

/** \ingroup header
 * Store header instance (e.g path or URL).
 * @param h		header
 * @param instance	new header instance
 * @return		0 always
 */
uint32_t headerSetInstance(/*@null@*/ Header h, uint32_t instance)
	/*@modifies h @*/;

/** \ingroup header
 * Return header starting byte offset.
 * @param h		header
 * @return		header starting byte offset 
 */
rpmuint32_t headerGetStartOff(/*@null@*/ Header h)
	/*@*/;

/** \ingroup header
 * Store header starting byte offset.
 * @param h		header
 * @param startoff	new header starting byte offset
 * @return		0 always
 */
rpmuint32_t headerSetStartOff(/*@null@*/ Header h, rpmuint32_t startoff)
	/*@modifies h @*/;

/** \ingroup header
 * Return header ending byte offset.
 * @param h		header
 * @return		header ending byte offset 
 */
rpmuint32_t headerGetEndOff(/*@null@*/ Header h)
	/*@*/;

/** \ingroup header
 * Store header ending byte offset.
 * @param h		header
 * @param startoff	new header ending byte offset
 * @return		0 always
 */
rpmuint32_t headerSetEndOff(/*@null@*/ Header h, rpmuint32_t endoff)
	/*@modifies h @*/;

/** \ingroup header
 * Return header stats accumulator structure.
 * @param h		header
 * @param opx		per-header accumulator index (aka rpmtsOpX)
 * @return		per-header accumulator pointer
 */
/*@null@*/
void * headerGetStats(Header h, int opx)
        /*@*/;

/**
 * Define per-header macros.
 * @param h		header
 * @return		0 always
 */
int headerMacrosLoad(Header h)
	/*@globals internalState @*/
	/*@modifies internalState @*/;

/**
 * Define per-header macros.
 * @param h		header
 * @return		0 always
 */
int headerMacrosUnload(Header h)
	/*@globals internalState @*/
	/*@modifies internalState @*/;

/** \ingroup header
 * Return name, epoch, version, release, arch strings from header.
 * @param h		header
 * @retval *np		name pointer (or NULL)
 * @retval *ep		epoch pointer (or NULL)
 * @retval *vp		version pointer (or NULL)
 * @retval *rp		release pointer (or NULL)
 * @retval *ap		arch pointer (or NULL)
 * @return		0 always
 */
int headerNEVRA(Header h,
		/*@null@*/ /*@out@*/ const char ** np,
		/*@null@*/ /*@out@*/ /*@unused@*/ const char ** ep,
		/*@null@*/ /*@out@*/ const char ** vp,
		/*@null@*/ /*@out@*/ const char ** rp,
		/*@null@*/ /*@out@*/ const char ** ap)
	/*@globals internalState @*/
	/*@modifies h, *np, *vp, *rp, *ap, internalState @*/;

/**
 * Return header color.
 * @param h		header
 * @return		header color
 */
rpmuint32_t hGetColor(Header h)
	/*@globals internalState @*/
	/*@modifies h, internalState @*/;

/** \ingroup header
 * Translate and merge legacy signature tags into header.
 * @todo Remove headerSort() through headerInitIterator() modifies sig.
 * @param h		header
 * @param sigh		signature header
 */
void headerMergeLegacySigs(Header h, const Header sigh)
	/*@globals fileSystem, internalState @*/
	/*@modifies h, sigh, fileSystem, internalState @*/;

/** \ingroup header
 * Regenerate signature header.
 * @todo Remove headerSort() through headerInitIterator() modifies h.
 * @param h		header
 * @param noArchiveSize	don't copy archive size tag (pre rpm-4.1)
 * @return		regenerated signature header
 */
Header headerRegenSigHeader(const Header h, int noArchiveSize)
	/*@globals fileSystem, internalState @*/
	/*@modifies h, fileSystem, internalState @*/;

#ifdef __cplusplus
}
#endif

#endif	/* H_RPMTAG */
