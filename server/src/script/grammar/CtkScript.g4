grammar CtkScript;
program: statement* EOF;
statement: 'let' Identifier '=' expression ';'             # assignment
         | 'emit' expression ';'                           # emission
         | 'save' expression 'to' expression 'as' Identifier ';' # saveStatement
         | expression ';'                                  # valueStatement
         | 'foreach' Identifier 'in' expression '{' statement* '}' # iteration;
expression: scalar                                      # literalExpression
          | '$'? Identifier ('[' Number ']')?            # referenceExpression
          | '[' (expression (',' expression)*)? ']'      # listExpression
          | '{' (objectKey ':' expression (',' objectKey ':' expression)*)? '}' # objectExpression
          | 'files' expression                          # filesExpression
          | 'foreach' Identifier 'in' expression 'do' '{' statement* '}' # foreachExpression
          | '(' expression ')'                           # groupedExpression
          | 'batch' Identifier 'in' expression ('size' sizeValue=Number | 'count' countValue=Number)
              ('jobs' jobsValue=Number)? ('memory' memoryValue=StringLiteral)? ('on' 'error' batchErrorPolicy)?
              ('progress' progressPolicy)? 'do' '{' statement* '}' # batchExpression
          | functionName '(' arguments? ')'             # callExpression
          | 'parse' StringLiteral                       # parseExpression
          | 'match' matcherExpression ('in' expression)? # matchExpression
          | expression '.' memberName                   # memberExpression
          | expression '[' expression ']'                # indexExpression
          | 'in' expression '{' statement* 'yield' expression ';' '}' # scopedExpression;
// These words are reserved by batch syntax but remain usable by legacy
// expression calls and collection keys/member access.
functionName: Identifier | 'match' | 'count' | 'continue';
batchErrorPolicy: 'stop' | 'continue';
progressPolicy: 'on' | 'off';
// Structure matcher calls in ANTLR; Clang performs overload and type checking.
matcherExpression: Identifier '(' matcherArguments? ')'
                   ('.' Identifier '(' matcherArguments? ')')*;
matcherArguments: matcherArgument (',' matcherArgument)*;
matcherArgument: matcherExpression | scalar | Identifier;
arguments: argument (',' argument)*;
argument: Identifier '=' expression                     # namedArgument
        | expression                                    # positionalArgument;
scalar: StringLiteral | Number | 'true' | 'false';
Identifier: [a-zA-Z_] [a-zA-Z_0-9]*;
StringLiteral: '"' (Escape | ~["\\\r\n])* '"';
fragment Escape: '\\' (["\\/bfnrt] | 'u' Hex Hex Hex Hex);
fragment Hex: [0-9a-fA-F];
Number: '-'? ('0' | [1-9][0-9]*) ('.' [0-9]+)? ([eE] [+-]? [0-9]+)?;
Whitespace: [ \t\r\n]+ -> skip;
Comment: '//' ~[\r\n]* -> skip;
memberName: Identifier | 'count' | 'continue';
objectKey: Identifier | StringLiteral | 'count' | 'continue';
