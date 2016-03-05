/* Requires GCC 4.7+ */

#include <znc/User.h>
#include <znc/znc.h>

using std::map;
using std::vector;

class CUserIPMod : public CModule {
  private:

    typedef map<CString, CUser*> MUsers;

    void ShowCommand(const CString& sLine) {
        if (!GetUser()->IsAdmin()) {
            PutModule("Access denied");
            return;
        }
    }

  public:

    MODCONSTRUCTOR(CUserIPMod) {}

    ~CUserIPMod() override {}

    // Web stuff:

    bool WebRequiresAdmin() override { return true; }
    CString GetWebMenuTitle() override { return "User IPs"; }

    bool OnWebRequest(CWebSock& WebSock, const CString& sPageName,
                      CTemplate& Tmpl) override {
        if (sPageName == "index") {
            CModules& GModules = CZNC::Get().GetModules();
            Tmpl["WebAdminLoaded"] =
                CString(GModules.FindModule("webadmin") != nullptr);

            const MUsers& mUsers = CZNC::Get().GetUserMap();

            for (MUsers::const_iterator it = mUsers.begin();
                 it != mUsers.end(); ++it) {
                CUser* pUser = it->second;
                CTemplate& Row = Tmpl.AddRow("UserLoop");
		Row["User"] = pUser->GetUserName();
		const std::vector<CClient*>& vClients = pUser->GetAllClients();
		CString cli = "";
		for (client:vClients) {
			cli.append(client->GetRemoteIP());
			cli.append(" ");
		}
		Row["IP"] = cli;
            }

            return true;
        }

        return false;
    }

};

template <>
void TModInfo<CUserIPMod>(CModInfo& Info) {}
GLOBALMODULEDEFS(CUserIPMod,
                 "Shows connected IPs for users.")
