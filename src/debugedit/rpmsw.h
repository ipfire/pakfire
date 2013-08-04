#ifndef	H_RPMSW
#define	H_RPMSW

/** \ingroup rpmio
 * \file rpmio/rpmsw.h
 */

/** \ingroup rpmio
 */
typedef unsigned long int rpmtime_t;

/** \ingroup rpmio
 */
typedef struct rpmsw_s * rpmsw;

/** \ingroup rpmio
 */
typedef struct rpmop_s * rpmop;

/** \ingroup rpmio
 */
struct rpmsw_s {
    union {
	struct timeval tv;
	unsigned long long int ticks;
	unsigned long int tocks[2];
    } u;
};

/** \ingroup rpmio
 * Cumulative statistics for an operation.
 */
struct rpmop_s {
    struct rpmsw_s	begin;	/*!< Starting time stamp. */
    int			count;	/*!< Number of operations. */
    unsigned long long	bytes;	/*!< Number of bytes transferred. */
    rpmtime_t		usecs;	/*!< Number of ticks. */
};

/*@unchecked@*/
extern int _rpmsw_stats;

/** \ingroup rpmio
 * Indices for timestamps.
 */
typedef	enum rpmswOpX_e {
    RPMSW_OP_TOTAL		=  0,
    RPMSW_OP_CHECK		=  1,
    RPMSW_OP_ORDER		=  2,
    RPMSW_OP_FINGERPRINT	=  3,
    RPMSW_OP_REPACKAGE		=  4,
    RPMSW_OP_INSTALL		=  5,
    RPMSW_OP_ERASE		=  6,
    RPMSW_OP_SCRIPTLETS		=  7,
    RPMSW_OP_COMPRESS		=  8,
    RPMSW_OP_UNCOMPRESS		=  9,
    RPMSW_OP_DIGEST		= 10,
    RPMSW_OP_SIGNATURE		= 11,
    RPMSW_OP_DBADD		= 12,
    RPMSW_OP_DBREMOVE		= 13,
    RPMSW_OP_DBGET		= 14,
    RPMSW_OP_DBPUT		= 15,
    RPMSW_OP_DBDEL		= 16,
    RPMSW_OP_READHDR		= 17,
    RPMSW_OP_HDRLOAD		= 18,
    RPMSW_OP_HDRGET		= 19,
    RPMSW_OP_DEBUG		= 20,
    RPMSW_OP_MAX		= 20
} rpmswOpX;

#ifdef __cplusplus
extern "C" {
#endif

/** Return benchmark time stamp.
 * @param *sw		time stamp
 * @return		0 on success
 */
/*@-exportlocal@*/
/*@null@*/
rpmsw rpmswNow(/*@returned@*/ rpmsw sw)
	/*@globals internalState @*/
	/*@modifies sw, internalState @*/;
/*@=exportlocal@*/

/** Return benchmark time stamp difference.
 * @param *end		end time stamp
 * @param *begin	begin time stamp
 * @return		difference in micro-seconds
 */
/*@-exportlocal@*/
rpmtime_t rpmswDiff(/*@null@*/ rpmsw end, /*@null@*/ rpmsw begin)
	/*@*/;
/*@=exportlocal@*/

/** Return benchmark time stamp overhead.
 * @return		overhead in micro-seconds
 */
/*@-exportlocal@*/
rpmtime_t rpmswInit(void)
	/*@globals internalState @*/
	/*@modifies internalState @*/;
/*@=exportlocal@*/

/** \ingroup rpmio
 * Enter timed operation.
 * @param op			operation statistics
 * @param rc			-1 clears usec counter
 * @return			0 always
 */
int rpmswEnter(/*@null@*/ rpmop op, ssize_t rc)
	/*@globals internalState @*/
	/*@modifies *op, internalState @*/;

/** \ingroup rpmio
 * Exit timed operation.
 * @param op			operation statistics
 * @param rc			per-operation data (e.g. bytes transferred)
 * @return			cumulative usecs for operation
 */
rpmtime_t rpmswExit(/*@null@*/ rpmop op, ssize_t rc)
	/*@globals internalState @*/
	/*@modifies op, internalState @*/;

/** \ingroup rpmio
 * Sum statistic counters.
 * @param to			result statistics
 * @param from			operation statistics
 * @return			cumulative usecs for operation
 */
rpmtime_t rpmswAdd(/*@null@*/ rpmop to, /*@null@*/ rpmop from)
	/*@modifies to @*/;

/** \ingroup rpmio
 * Subtract statistic counters.
 * @param to			result statistics
 * @param from			operation statistics
 * @return			cumulative usecs for operation
 */
rpmtime_t rpmswSub(rpmop to, rpmop from)
	/*@modifies to @*/;

/** \ingroup rpmio
 * Print operation statistics.
 * @param name			operation name
 * @param op			operation statistics
 * @param fp			file handle (NULL uses stderr)
 */
void rpmswPrint(const char * name, /*@null@*/ rpmop op, /*@null@*/ FILE * fp)
        /*@globals fileSystem @*/
        /*@modifies fp, fileSystem @*/;

#ifdef __cplusplus
}
#endif

#endif	/* H_RPMSW */
