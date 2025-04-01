import re


class TestSlack:
    def test_slack_regex(self):
        reg = re.compile("<@.+?>")
        assert (
            len(
                reg.findall(
                    "abcd <@abcd>  lkdsfgsdkljfgn sjkdfgb kljdfnga./sdfgms dlkfgnm.sdklfj ng.kjdwnf34hiu 3r4 > \n adsfgsdf gsdfg sdf<FDG ADSFGA> DSFGA DFGADSF< ASDFG> <DSAFG<<G ADSF>GADF @ sdfasd <@a-bc.23>"
                )
            )
            == 2
        )
