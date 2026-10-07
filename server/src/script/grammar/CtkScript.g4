grammar CtkScript;
program: statement* EOF;
statement: 'let' Identifier '=' expression ';'             # assignment
         | 'emit' expression ';'                           # emission
         | 'foreach' Identifier 'in' expression '{' statement* '}' # iteration;
expression: scalar                                      # literalExpression
          | '$'? Identifier ('[' Number ']')?            # referenceExpression
          | functionName '(' arguments? ')'             # callExpression
          | 'parse' StringLiteral                       # parseExpression
          | 'match' matcherExpression ('in' matchTarget)? # matchExpression
          | 'in' expression '{' statement* 'yield' expression ';' '}' # scopedExpression;
functionName: Identifier | 'match';
matchTarget: StringLiteral | '$' Identifier ('[' Number ']')? ('.' Identifier)?;
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
