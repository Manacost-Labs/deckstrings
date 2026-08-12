namespace ManacostLabs.Deckstrings
{
    internal static class TextRules
    {
        private static readonly char[] ExportWhitespace =
        {
            '\u0009', '\u000A', '\u000B', '\u000C', '\u000D', '\u0020',
            '\u0085', '\u00A0', '\u1680', '\u2000', '\u2001', '\u2002',
            '\u2003', '\u2004', '\u2005', '\u2006', '\u2007', '\u2008',
            '\u2009', '\u200A', '\u2028', '\u2029', '\u202F', '\u205F',
            '\u3000',
        };

        internal static string TrimExportWhitespace(string value)
        {
            return value.Trim(ExportWhitespace);
        }

        internal static bool IsExportBlank(string value)
        {
            return TrimExportWhitespace(value).Length == 0;
        }

        internal static bool ContainsLineBreak(string value)
        {
            for (var index = 0; index < value.Length; index++)
            {
                if (value[index] == '\r' || value[index] == '\n')
                {
                    return true;
                }
            }

            return false;
        }

        internal static bool IsWellFormedUnicode(string value)
        {
            for (var index = 0; index < value.Length; index++)
            {
                var codeUnit = value[index];
                if (char.IsHighSurrogate(codeUnit))
                {
                    if (index + 1 >= value.Length || !char.IsLowSurrogate(value[index + 1]))
                    {
                        return false;
                    }

                    index++;
                }
                else if (char.IsLowSurrogate(codeUnit))
                {
                    return false;
                }
            }

            return true;
        }
    }
}
