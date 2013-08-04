#ifndef _H_RPMIOTYPES_
#define	_H_RPMIOTYPES_

/** \ingroup rpmio
 * \file rpmio/rpmiotypes.h
 */

/** \ingroup rpmio
 * RPM return codes.
 */
typedef	enum rpmRC_e {
    RPMRC_OK		= 0,	/*!< Generic success code */
    RPMRC_NOTFOUND	= 1,	/*!< Generic not found code. */
    RPMRC_FAIL		= 2,	/*!< Generic failure code. */
    RPMRC_NOTTRUSTED	= 3,	/*!< Signature is OK, but key is not trusted. */
    RPMRC_NOKEY		= 4	/*!< Public key is unavailable. */
} rpmRC;

/** \ingroup rpmio
 * Private int typedefs to avoid C99 portability issues.
 */
typedef	/*@unsignedintegraltype@*/	unsigned char		rpmuint8_t;
typedef /*@unsignedintegraltype@*/	unsigned short		rpmuint16_t;
typedef /*@unsignedintegraltype@*/	unsigned int		rpmuint32_t;
typedef /*@unsignedintegraltype@*/	unsigned long long	rpmuint64_t;

/** \ingroup rpmio
 */
typedef /*@signedintegraltype@*/	int			rpmint32_t;

/**
 */
typedef	/*@refcounted@*/ struct rpmioItem_s * rpmioItem;
struct rpmioItem_s {
/*@null@*/
    void *use;			/*!< use count -- return to pool when zero */
/*@kept@*/ /*@null@*/
    void *pool;			/*!< pool (or NULL if malloc'd) */
#if defined(__LCLINT__)
/*@refs@*/
    int nrefs;			/*!< (unused) keep splint happy */
#endif
};

/**
 */
typedef struct rpmioPool_s * rpmioPool;

/** \ingroup rpmio
 */
typedef /*@abstract@*/ /*@refcounted@*/ struct rpmiob_s * rpmiob;

/** \ingroup rpmio
 */
/*@unchecked@*/
extern size_t _rpmiob_chunk;

/** \ingroup rpmio
 */
typedef struct rpmioP_s {
    char * str;
    char * next;
    const char ** av;
    int ac;
} * rpmioP;

/** \ingroup rpmpgp
 */
typedef /*@abstract@*/ struct DIGEST_CTX_s * DIGEST_CTX;

/** \ingroup rpmpgp
 */
typedef /*@abstract@*/ struct pgpPkt_s * pgpPkt;

/** \ingroup rpmpgp
 */
typedef /*@abstract@*/ /*@refcounted@*/ struct pgpDig_s * pgpDig;

/** \ingroup rpmpgp
 */
typedef /*@abstract@*/ struct pgpDigParams_s * pgpDigParams;

/** \ingroup rpmpgp
 */
typedef rpmuint8_t pgpKeyID_t[8];

/** \ingroup rpmpgp
 */
typedef rpmuint8_t pgpTime_t[4];

/** \ingroup rpmpgp
 * Bit(s) to control digest and signature verification.
 */
typedef enum pgpVSFlags_e {
    RPMVSF_DEFAULT	= 0,
    RPMVSF_NOHDRCHK	= (1 <<  0),
    RPMVSF_NEEDPAYLOAD	= (1 <<  1),
    /* bit(s) 2-7 unused */
    RPMVSF_NOSHA1HEADER	= (1 <<  8),
    RPMVSF_NOMD5HEADER	= (1 <<  9),	/* unimplemented */
    RPMVSF_NODSAHEADER	= (1 << 10),
    RPMVSF_NORSAHEADER	= (1 << 11),
    /* bit(s) 12-15 unused */
    RPMVSF_NOSHA1	= (1 << 16),	/* unimplemented */
    RPMVSF_NOMD5	= (1 << 17),
    RPMVSF_NODSA	= (1 << 18),
    RPMVSF_NORSA	= (1 << 19)
    /* bit(s) 20-31 unused */
} pgpVSFlags;

#define	_RPMVSF_NODIGESTS	\
  ( RPMVSF_NOSHA1HEADER |	\
    RPMVSF_NOMD5HEADER |	\
    RPMVSF_NOSHA1 |		\
    RPMVSF_NOMD5 )

#define	_RPMVSF_NOSIGNATURES	\
  ( RPMVSF_NODSAHEADER |	\
    RPMVSF_NORSAHEADER |	\
    RPMVSF_NODSA |		\
    RPMVSF_NORSA )

#define	_RPMVSF_NOHEADER	\
  ( RPMVSF_NOSHA1HEADER |	\
    RPMVSF_NOMD5HEADER |	\
    RPMVSF_NODSAHEADER |	\
    RPMVSF_NORSAHEADER )

#define	_RPMVSF_NOPAYLOAD	\
  ( RPMVSF_NOSHA1 |		\
    RPMVSF_NOMD5 |		\
    RPMVSF_NODSA |		\
    RPMVSF_NORSA )

/*@-redef@*/ /* LCL: ??? */
typedef /*@abstract@*/ const void * fnpyKey;
/*@=redef@*/

/**
 * Bit(s) to identify progress callbacks.
 */
typedef enum rpmCallbackType_e {
    RPMCALLBACK_UNKNOWN         = 0,
    RPMCALLBACK_INST_PROGRESS   = (1 <<  0),
    RPMCALLBACK_INST_START      = (1 <<  1),
    RPMCALLBACK_INST_OPEN_FILE  = (1 <<  2),
    RPMCALLBACK_INST_CLOSE_FILE = (1 <<  3),
    RPMCALLBACK_TRANS_PROGRESS  = (1 <<  4),
    RPMCALLBACK_TRANS_START     = (1 <<  5),
    RPMCALLBACK_TRANS_STOP      = (1 <<  6),
    RPMCALLBACK_UNINST_PROGRESS = (1 <<  7),
    RPMCALLBACK_UNINST_START    = (1 <<  8),
    RPMCALLBACK_UNINST_STOP     = (1 <<  9),
    RPMCALLBACK_REPACKAGE_PROGRESS = (1 << 10),
    RPMCALLBACK_REPACKAGE_START = (1 << 11),
    RPMCALLBACK_REPACKAGE_STOP  = (1 << 12),
    RPMCALLBACK_UNPACK_ERROR    = (1 << 13),
    RPMCALLBACK_CPIO_ERROR      = (1 << 14),
    RPMCALLBACK_SCRIPT_ERROR    = (1 << 15)
} rpmCallbackType;

/**
 */
typedef void * rpmCallbackData;

/** \ingroup rpmpgp
 * 9.4. Hash Algorithms
 *
\verbatim
       ID           Algorithm                              Text Name
       --           ---------                              ---- ----
       1          - MD5                                    "MD5"
       2          - SHA-1                                  "SHA1"
       3          - RIPE-MD/160                            "RIPEMD160"
       4          - Reserved for double-width SHA (experimental)
       5          - MD2                                    "MD2"
       6          - Reserved for TIGER/192                 "TIGER192"
       7          - Reserved for HAVAL (5 pass, 160-bit)   "HAVAL-5-160"
       100 to 110 - Private/Experimental algorithm.
\endverbatim
 *
 * Implementations MUST implement SHA-1. Implementations SHOULD
 * implement MD5.
 * @todo Add SHA256.
 */
typedef enum pgpHashAlgo_e {
    PGPHASHALGO_ERROR		=  -1,
    PGPHASHALGO_NONE		=  0,
    PGPHASHALGO_MD5		=  1,	/*!< MD5 */
    PGPHASHALGO_SHA1		=  2,	/*!< SHA-1 */
    PGPHASHALGO_RIPEMD160	=  3,	/*!< RIPEMD-160 */
    PGPHASHALGO_MD2		=  5,	/*!< MD2 */
    PGPHASHALGO_TIGER192	=  6,	/*!< TIGER-192 */
    PGPHASHALGO_HAVAL_5_160	=  7,	/*!< HAVAL-5-160 */
    PGPHASHALGO_SHA256		=  8,	/*!< SHA-256 */
    PGPHASHALGO_SHA384		=  9,	/*!< SHA-384 */
    PGPHASHALGO_SHA512		= 10,	/*!< SHA-512 */
    PGPHASHALGO_SHA224		= 11,	/*!< SHA-224 */

    PGPHASHALGO_MD4		= 104,	/*!< (private) MD4 */
    PGPHASHALGO_RIPEMD128	= 105,	/*!< (private) RIPEMD-128 */
    PGPHASHALGO_CRC32		= 106,	/*!< (private) CRC-32 */
    PGPHASHALGO_ADLER32		= 107,	/*!< (private) ADLER-32 */
    PGPHASHALGO_CRC64		= 108,	/*!< (private) CRC-64 */
    PGPHASHALGO_JLU32		= 109,	/*!< (private) Jenkins lookup3.c */

    PGPHASHALGO_RIPEMD256	= 111,	/*!< (private) RIPEMD-256 */
    PGPHASHALGO_RIPEMD320	= 112,	/*!< (private) RIPEMD-320 */
    PGPHASHALGO_SALSA10		= 113,	/*!< (private) SALSA-10 */
    PGPHASHALGO_SALSA20		= 114,	/*!< (private) SALSA-20 */

    PGPHASHALGO_MD6_224		= 128+0,/*!< (private) MD6-224 */
    PGPHASHALGO_MD6_256		= 128+1,/*!< (private) MD6-256 */
    PGPHASHALGO_MD6_384		= 128+2,/*!< (private) MD6-384 */
    PGPHASHALGO_MD6_512		= 128+3,/*!< (private) MD6-512 */

    PGPHASHALGO_CUBEHASH_224	= 136+0,/*!< (private) CUBEHASH-224 */
    PGPHASHALGO_CUBEHASH_256	= 136+1,/*!< (private) CUBEHASH-256 */
    PGPHASHALGO_CUBEHASH_384	= 136+2,/*!< (private) CUBEHASH-384 */
    PGPHASHALGO_CUBEHASH_512	= 136+3,/*!< (private) CUBEHASH-512 */

    PGPHASHALGO_KECCAK_224	= 144+0,/*!< (private) KECCAK-224 */
    PGPHASHALGO_KECCAK_256	= 144+1,/*!< (private) KECCAK-256 */
    PGPHASHALGO_KECCAK_384	= 144+2,/*!< (private) KECCAK-384 */
    PGPHASHALGO_KECCAK_512	= 144+3,/*!< (private) KECCAK-384 */

    PGPHASHALGO_ECHO_224	= 148+0,/*!< (private) ECHO-224 */
    PGPHASHALGO_ECHO_256	= 148+1,/*!< (private) ECHO-256 */
    PGPHASHALGO_ECHO_384	= 148+2,/*!< (private) ECHO-384 */
    PGPHASHALGO_ECHO_512	= 148+3,/*!< (private) ECHO-384 */

    PGPHASHALGO_EDONR_224	= 152+0,/*!< (private) EDON-R-224 */
    PGPHASHALGO_EDONR_256	= 152+1,/*!< (private) EDON-R-256 */
    PGPHASHALGO_EDONR_384	= 152+2,/*!< (private) EDON-R-384 */
    PGPHASHALGO_EDONR_512	= 152+3,/*!< (private) EDON-R-512 */

    PGPHASHALGO_FUGUE_224	= 156+0,/*!< (private) FUGUE-224 */
    PGPHASHALGO_FUGUE_256	= 156+1,/*!< (private) FUGUE-256 */
    PGPHASHALGO_FUGUE_384	= 156+2,/*!< (private) FUGUE-384 */
    PGPHASHALGO_FUGUE_512	= 156+3,/*!< (private) FUGUE-512 */

    PGPHASHALGO_SKEIN_224	= 160+0,/*!< (private) SKEIN-224 */
    PGPHASHALGO_SKEIN_256	= 160+1,/*!< (private) SKEIN-256 */
    PGPHASHALGO_SKEIN_384	= 160+2,/*!< (private) SKEIN-384 */
    PGPHASHALGO_SKEIN_512	= 160+3,/*!< (private) SKEIN-512 */
    PGPHASHALGO_SKEIN_1024	= 160+4,/*!< (private) SKEIN-1024 */

    PGPHASHALGO_BMW_224		= 168+0,/*!< (private) BMW-224 */
    PGPHASHALGO_BMW_256		= 168+1,/*!< (private) BMW-256 */
    PGPHASHALGO_BMW_384		= 168+2,/*!< (private) BMW-384 */
    PGPHASHALGO_BMW_512		= 168+3,/*!< (private) BMW-512 */

    PGPHASHALGO_SHABAL_224	= 176+0,/*!< (private) SHABAL-224 */
    PGPHASHALGO_SHABAL_256	= 176+1,/*!< (private) SHABAL-256 */
    PGPHASHALGO_SHABAL_384	= 176+2,/*!< (private) SHABAL-384 */
    PGPHASHALGO_SHABAL_512	= 176+3,/*!< (private) SHABAL-512 */

    PGPHASHALGO_SHAVITE3_224	= 180+0,/*!< (private) SHAVITE3-224 */
    PGPHASHALGO_SHAVITE3_256	= 180+1,/*!< (private) SHAVITE3-256 */
    PGPHASHALGO_SHAVITE3_384	= 180+2,/*!< (private) SHAVITE3-384 */
    PGPHASHALGO_SHAVITE3_512	= 180+3,/*!< (private) SHAVITE3-512 */

    PGPHASHALGO_BLAKE_224	= 184+0,/*!< (private) BLAKE-224 */
    PGPHASHALGO_BLAKE_256	= 184+1,/*!< (private) BLAKE-256 */
    PGPHASHALGO_BLAKE_384	= 184+2,/*!< (private) BLAKE-384 */
    PGPHASHALGO_BLAKE_512	= 184+3,/*!< (private) BLAKE-512 */

    PGPHASHALGO_TIB3_224	= 192+0,/*!< (private) TIB3-224 */
    PGPHASHALGO_TIB3_256	= 192+1,/*!< (private) TIB3-256 */
    PGPHASHALGO_TIB3_384	= 192+2,/*!< (private) TIB3-384 */
    PGPHASHALGO_TIB3_512	= 192+3,/*!< (private) TIB3-512 */

    PGPHASHALGO_SIMD_224	= 200+0,/*!< (private) SIMD-224 */
    PGPHASHALGO_SIMD_256	= 200+1,/*!< (private) SIMD-256 */
    PGPHASHALGO_SIMD_384	= 200+2,/*!< (private) SIMD-384 */
    PGPHASHALGO_SIMD_512	= 200+3,/*!< (private) SIMD-512 */

    PGPHASHALGO_ARIRANG_224	= 208+0,/*!< (private) ARIRANG-224 */
    PGPHASHALGO_ARIRANG_256	= 208+1,/*!< (private) ARIRANG-256 */
    PGPHASHALGO_ARIRANG_384	= 208+2,/*!< (private) ARIRANG-384 */
    PGPHASHALGO_ARIRANG_512	= 208+3,/*!< (private) ARIRANG-512 */

    PGPHASHALGO_LANE_224	= 212+0,/*!< (private) LANE-224 */
    PGPHASHALGO_LANE_256	= 212+1,/*!< (private) LANE-256 */
    PGPHASHALGO_LANE_384	= 212+2,/*!< (private) LANE-384 */
    PGPHASHALGO_LANE_512	= 212+3,/*!< (private) LANE-512 */

    PGPHASHALGO_LUFFA_224	= 216+0,/*!< (private) LUFFA-224 */
    PGPHASHALGO_LUFFA_256	= 216+1,/*!< (private) LUFFA-256 */
    PGPHASHALGO_LUFFA_384	= 216+2,/*!< (private) LUFFA-384 */
    PGPHASHALGO_LUFFA_512	= 216+3,/*!< (private) LUFFA-512 */

    PGPHASHALGO_CHI_224		= 224+0,/*!< (private) CHI-224 */
    PGPHASHALGO_CHI_256		= 224+1,/*!< (private) CHI-256 */
    PGPHASHALGO_CHI_384		= 224+2,/*!< (private) CHI-384 */
    PGPHASHALGO_CHI_512		= 224+3,/*!< (private) CHI-512 */

    PGPHASHALGO_JH_224		= 232+0,/*!< (private) JH-224 */
    PGPHASHALGO_JH_256		= 232+1,/*!< (private) JH-256 */
    PGPHASHALGO_JH_384		= 232+2,/*!< (private) JH-384 */
    PGPHASHALGO_JH_512		= 232+3,/*!< (private) JH-512 */

    PGPHASHALGO_GROESTL_224	= 240+0,/*!< (private) GROESTL-224 */
    PGPHASHALGO_GROESTL_256	= 240+1,/*!< (private) GROESTL-256 */
    PGPHASHALGO_GROESTL_384	= 240+2,/*!< (private) GROESTL-384 */
    PGPHASHALGO_GROESTL_512	= 240+3,/*!< (private) GROESTL-512 */

    PGPHASHALGO_HAMSI_224	= 248+0,/*!< (private) HAMSI-224 */
    PGPHASHALGO_HAMSI_256	= 248+1,/*!< (private) HAMSI-256 */
    PGPHASHALGO_HAMSI_384	= 248+2,/*!< (private) HAMSI-384 */
    PGPHASHALGO_HAMSI_512	= 248+3,/*!< (private) HAMSI-512 */

} pgpHashAlgo;

/** \ingroup rpmpgp
 * Bit(s) to control digest operation.
 */
typedef enum rpmDigestFlags_e {
    RPMDIGEST_NONE	=	0,
} rpmDigestFlags;

#if defined(_RPMIOB_INTERNAL)
/** \ingroup rpmio
 */
struct rpmiob_s{
    struct rpmioItem_s _item;	/*!< usage mutex and pool identifier. */
    rpmuint8_t * b;		/*!< data octects. */
    size_t blen;		/*!< no. of octets used. */
    size_t allocated;		/*!< no. of octets allocated. */
#if defined(__LCLINT__)
/*@refs@*/
    int nrefs;				/*!< (unused) keep splint happy */
#endif
};
#endif

#ifdef __cplusplus
extern "C" {
#endif

/** \ingroup rpmpgp
 * Return digest algorithm identifier.
 * @param ctx		digest context
 * @return		digest hash algorithm identifier
 */
pgpHashAlgo rpmDigestAlgo(DIGEST_CTX ctx)
	/*@*/;

/** \ingroup rpmpgp
 * Return digest flags.
 * @param ctx		digest context
 * @return		digest flags
 */
rpmDigestFlags rpmDigestF(DIGEST_CTX ctx)
	/*@*/;

/** \ingroup rpmpgp
 * Return digest name.
 * @param ctx		digest context
 * @return		digest name
 */
/*@observer@*/
const char * rpmDigestName(DIGEST_CTX ctx)
	/*@*/;

/** \ingroup rpmpgp
 * Return digest ASN1 oid string.
 * Values from PKCS#1 v2.1 (aka RFC-3447).
 * @param ctx		digest context
 * @return		digest ASN1 oid string
 */
/*@observer@*/ /*@null@*/
const char * rpmDigestASN1(DIGEST_CTX ctx)
	/*@*/;

/** \ingroup rpmpgp
 * Duplicate a digest context.
 * @param octx		existing digest context
 * @return		duplicated digest context
 */
/*@only@*/
DIGEST_CTX rpmDigestDup(DIGEST_CTX octx)
	/*@*/;

/** \ingroup rpmpgp
 * Initialize digest.
 * Set bit count to 0 and buffer to mysterious initialization constants.
 * @param hashalgo	type of digest
 * @param flags		bit(s) to control digest operation
 * @return		digest context
 */
/*@only@*/ /*@null@*/
DIGEST_CTX rpmDigestInit(pgpHashAlgo hashalgo, rpmDigestFlags flags)
	/*@*/;

/** \ingroup rpmpgp
 * Update context with next plain text buffer.
 * @param ctx		digest context
 * @param data		next data buffer
 * @param len		no. bytes of data
 * @return		0 on success
 */
int rpmDigestUpdate(/*@null@*/ DIGEST_CTX ctx, const void * data, size_t len)
	/*@modifies ctx @*/;

/** \ingroup rpmpgp
 * Return digest and destroy context.
 *
 * @param ctx		digest context
 * @retval *datap	digest
 * @retval *lenp	no. bytes of digest
 * @param asAscii	return digest as ascii string?
 * @return		0 on success
 */
int rpmDigestFinal(/*@only@*/ /*@null@*/ DIGEST_CTX ctx,
	/*@null@*/ /*@out@*/ void * datap,
	/*@null@*/ /*@out@*/ size_t * lenp, int asAscii)
		/*@modifies *datap, *lenp @*/;

/** \ingroup rpmpgp
 *
 * Compute key material and add to digest context.
 * @param ctx		digest context
 * @param key		HMAC key (NULL does digest instead)
 * @param keylen	HMAC key length(bytes) (0 uses strlen(key))
 * @return		0 on success
 */
int rpmHmacInit(DIGEST_CTX ctx, const void * key, size_t keylen)
	/*@*/;

/** \ingroup rpmio
 */
typedef void * (*rpmCallbackFunction)
                (/*@null@*/ const void * h,
                const rpmCallbackType what,
                const rpmuint64_t amount,
                const rpmuint64_t total,
                /*@null@*/ fnpyKey key,
                /*@null@*/ rpmCallbackData data)
        /*@globals internalState@*/
        /*@modifies internalState@*/;

#if !defined(SWIG)
/** \ingroup rpmio
 * Wrapper to free(3), hides const compilation noise, permit NULL, return NULL.
 * @param p		memory to free
 * @return		NULL always
 */
#if defined(WITH_DMALLOC)
#define _free(p) ((p) != NULL ? free((void *)(p)) : (void)0, NULL)
#else
/*@unused@*/ static inline /*@null@*/
void * _free(/*@only@*/ /*@null@*/ /*@out@*/ const void * p)
	/*@modifies p @*/
{
    if (p != NULL)	free((void *)p);
    return NULL;
}
#endif
#endif

/*@unused@*/ static inline int xislower(int c) /*@*/ {
    return (c >= (int)'a' && c <= (int)'z');
}
/*@unused@*/ static inline int xisupper(int c) /*@*/ {
    return (c >= (int)'A' && c <= (int)'Z');
}
/*@unused@*/ static inline int xisalpha(int c) /*@*/ {
    return (xislower(c) || xisupper(c));
}
/*@unused@*/ static inline int xisdigit(int c) /*@*/ {
    return (c >= (int)'0' && c <= (int)'9');
}
/*@unused@*/ static inline int xisalnum(int c) /*@*/ {
    return (xisalpha(c) || xisdigit(c));
}
/*@unused@*/ static inline int xisblank(int c) /*@*/ {
    return (c == (int)' ' || c == (int)'\t');
}
/*@unused@*/ static inline int xisspace(int c) /*@*/ {
    return (xisblank(c) || c == (int)'\n' || c == (int)'\r' || c == (int)'\f' || c == (int)'\v');
}
/*@unused@*/ static inline int xiscntrl(int c) /*@*/ {
    return (c < (int)' ');
}
/*@unused@*/ static inline int xisascii(int c) /*@*/ {
    return ((c & 0x80) != 0x80);
}
/*@unused@*/ static inline int xisprint(int c) /*@*/ {
    return (c >= (int)' ' && xisascii(c));
}
/*@unused@*/ static inline int xisgraph(int c) /*@*/ {
    return (c > (int)' ' && xisascii(c));
}
/*@unused@*/ static inline int xispunct(int c) /*@*/ {
    return (xisgraph(c) && !xisalnum(c));
}

/*@unused@*/ static inline int xtolower(int c) /*@*/ {
    return ((xisupper(c)) ? (c | ('a' - 'A')) : c);
}
/*@unused@*/ static inline int xtoupper(int c) /*@*/ {
    return ((xislower(c)) ? (c & ~('a' - 'A')) : c);
}

/** \ingroup rpmio
 * Locale insensitive strcasecmp(3).
 */
int xstrcasecmp(const char * s1, const char * s2)		/*@*/;

/** \ingroup rpmio
 * Locale insensitive strncasecmp(3).
 */
int xstrncasecmp(const char *s1, const char * s2, size_t n)	/*@*/;

/** \ingroup rpmio
 * Force encoding of string.
 */
/*@only@*/ /*@null@*/
const char * xstrtolocale(/*@only@*/ const char *str)
	/*@modifies *str @*/;

/**
 * Unreference a I/O buffer instance.
 * @param iob		hash table
 * @return		NULL if free'd
 */
/*@unused@*/ /*@null@*/
rpmiob rpmiobUnlink (/*@killref@*/ /*@null@*/ rpmiob iob)
	/*@globals fileSystem @*/
	/*@modifies iob, fileSystem @*/;
#define	rpmiobUnlink(_iob)	\
    ((rpmiob)rpmioUnlinkPoolItem((rpmioItem)(_iob), __FUNCTION__, __FILE__, __LINE__))

/**
 * Reference a I/O buffer instance.
 * @param iob		I/O buffer
 * @return		new I/O buffer reference
 */
/*@unused@*/ /*@newref@*/ /*@null@*/
rpmiob rpmiobLink (/*@null@*/ rpmiob iob)
	/*@globals fileSystem @*/
	/*@modifies iob, fileSystem @*/;
#define	rpmiobLink(_iob)	\
    ((rpmiob)rpmioLinkPoolItem((rpmioItem)(_iob), __FUNCTION__, __FILE__, __LINE__))

/**
 * Destroy a I/O buffer instance.
 * @param iob		I/O buffer
 * @return		NULL on last dereference
 */
/*@null@*/
rpmiob rpmiobFree( /*@killref@*/ rpmiob iob)
	/*@globals fileSystem @*/
	/*@modifies iob, fileSystem @*/;
#define	rpmiobFree(_iob)	\
    ((rpmiob)rpmioFreePoolItem((rpmioItem)(_iob), __FUNCTION__, __FILE__, __LINE__))

/**
 * Create an I/O buffer.
 * @param len		no. of octets to allocate
 * @return		new I/O buffer
 */
/*@newref@*/ /*@null@*/
rpmiob rpmiobNew(size_t len)
	/*@globals fileSystem @*/
	/*@modifies fileSystem @*/;

/**
 * Empty an I/O buffer.
 * @param iob		I/O buffer
 * @return		I/O buffer
 */
rpmiob rpmiobEmpty(/*@returned@*/ rpmiob iob)
	/*@modifies iob @*/;

/**
 * Trim trailing white space.
 * @param iob		I/O buffer
 * @return		I/O buffer
 */
rpmiob rpmiobRTrim(/*@returned@*/ rpmiob iob)
	/*@modifies iob @*/;

/**
 * Append string to I/O buffer.
 * @param iob		I/O buffer
 * @param s		string
 * @param nl		append NL?
 * @return		I/O buffer
 */
rpmiob rpmiobAppend(/*@returned@*/ rpmiob iob, const char * s, size_t nl)
	/*@modifies iob @*/;

/**
 * Return I/O buffer.
 * @param iob		I/O buffer
 * @return		I/O buffer (as octets)
 */
rpmuint8_t * rpmiobBuf(rpmiob iob)
	/*@*/;

/**
 * Return I/O buffer (as string).
 * @param iob		I/O buffer
 * @return		I/O buffer (as string)
 */
char * rpmiobStr(rpmiob iob)
	/*@*/;

/**
 * Return I/O buffer len.
 * @param iob		I/O buffer
 * @return		I/O buffer length
 */
size_t rpmiobLen(rpmiob iob)
	/*@*/;

#if defined(_RPMIOB_INTERNAL)
/**
 * Read an entire file into a buffer.
 * @param fn		file name to read
 * @retval *iobp	I/O buffer
 * @return		0 on success
 */
int rpmiobSlurp(const char * fn, rpmiob * iobp)
        /*@globals h_errno, fileSystem, internalState @*/
        /*@modifies *iobp, fileSystem, internalState @*/;
#endif

/**
 * Destroy a rpmioP object.
 * @param P		parser state
 * @return		NULL
 */
/*@null@*/
rpmioP rpmioPFree(/*@only@*/ /*@null@*/ rpmioP P)
	/*@modifies P @*/;

/**
 * Parse next command out of a string incrementally.
 * @param *Pptr		parser state
 * @param str		string to parse
 * @return		RPMRC_OK on success
 */
rpmRC rpmioParse(rpmioP *Pptr, const char * str)
	/*@modifies *Pptr @*/;

#ifdef __cplusplus
}
#endif

#endif /* _H_RPMIOTYPES_ */
