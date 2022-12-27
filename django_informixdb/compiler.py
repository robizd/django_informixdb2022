from django.db.models.sql import compiler


class SQLCompiler(compiler.SQLCompiler):
    def as_sql(self, with_limits=True, with_col_aliases=False):
        raw_sql, fields = super(SQLCompiler, self).as_sql(False, with_col_aliases)

        # MMS
        #print(">>>>>>> raw_sql(before): {}".format(raw_sql))
        #print(">>>>>>> fields(before): {}".format(fields))

        # special dialect to return first n rows
        if with_limits:
            if self.query.high_mark is not None:
                _select = "SELECT"
                _first = self.query.high_mark
                if self.query.low_mark:
                    _select += " SKIP %s" % self.query.low_mark
                    _first -= self.query.low_mark
                _select += " FIRST %s" % _first
                raw_sql = raw_sql.replace("SELECT", _select, 1)
        
        # MMS BEGIN
        # Informix ODBC doesn't tolerate parameters in projection clause. Let's apply them.
        # Only until first FROM
        mms_ffrom = raw_sql.find("FROM")
        #print(">>>>>>> mms_ffrom: {}".format(mms_ffrom))
        mms_paramapplied = 0
        #print(">>>>>>> mms_paramapplied: {}".format(mms_paramapplied))
        # Iterate over parameters and apply
        for mms_param in fields:
            #print(">>>>>>> mms_param: {}".format(mms_param))
            mms_curparam = raw_sql.find("%s")
            #print(">>>>>>> mms_curparam: {}".format(mms_curparam))
            if mms_curparam < 0 or mms_curparam > mms_ffrom:
                #print(">>>>>>> No more projection clause params. mms_curparam: {} > mms_ffrom: {}".format(mms_curparam, mms_ffrom))
                break
            raw_sql = raw_sql[0:mms_curparam] + "{}".format(mms_param) + raw_sql[mms_curparam + 2:]
            #print(">>>>>>> raw_sql(after): {}".format(raw_sql))
            mms_paramapplied += 1
            #print(">>>>>>> mms_paramapplied: {}".format(mms_paramapplied))
        
        # Remove applied parameters 
        if mms_paramapplied > 0:
            fields = tuple(list(fields)[mms_paramapplied:])
        
        # MMS END
        #print(">>>>>>> raw_sql(after): {}".format(raw_sql))
        #print(">>>>>>> fields(before): {}".format(fields))
        
        return raw_sql.replace(r'%s', '?'), fields


def _list2tuple(arg):
    return tuple(arg) if isinstance(arg, list) else arg


class SQLInsertCompiler(compiler.SQLInsertCompiler, SQLCompiler):
    def as_sql(self):
        result = super(SQLInsertCompiler, self).as_sql()
        return [(ret[0].replace(r'%s', '?'), _list2tuple(ret[1])) for ret in result]


class SQLAggregateCompiler(compiler.SQLAggregateCompiler, SQLCompiler):
    def as_sql(self):
        result = super(SQLAggregateCompiler, self).as_sql()
        return result[0].replace(r'%s', '?'), result[1]


class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SQLCompiler):
    def as_sql(self):
        result = super(SQLDeleteCompiler, self).as_sql()
        return result[0].replace(r'%s', '?'), result[1]


class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SQLCompiler):
    def as_sql(self):
        result = super(SQLUpdateCompiler, self).as_sql()
        return result[0].replace(r'%s', '?'), result[1]
