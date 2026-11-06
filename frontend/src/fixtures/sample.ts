export const activity = [
{time:'09:00',normal:180,suspicious:8},{time:'09:15',normal:220,suspicious:12},
{time:'09:30',normal:195,suspicious:9},{time:'09:45',normal:310,suspicious:18},
{time:'10:00',normal:265,suspicious:15},{time:'10:15',normal:290,suspicious:42},
{time:'10:30',normal:245,suspicious:76},{time:'10:45',normal:330,suspicious:32},
{time:'11:00',normal:295,suspicious:21},{time:'11:15',normal:370,suspicious:16},
{time:'11:30',normal:320,suspicious:12},{time:'11:45',normal:350,suspicious:19}];
export const totals = activity.reduce((a,r)=>({normal:a.normal+r.normal,suspicious:a.suspicious+r.suspicious}),{normal:0,suspicious:0});
export const flows = [
{id:'FL-0284',source:'192.168.1.24',destination:'10.0.0.8',port:443,label:'Suspicious',reason:'Illustrative burst of outbound connections'},
{id:'FL-0281',source:'192.168.1.16',destination:'10.0.0.12',port:22,label:'Suspicious',reason:'Illustrative repeated connection attempts'},
{id:'FL-0276',source:'192.168.1.42',destination:'10.0.0.8',port:80,label:'Suspicious',reason:'Illustrative unusual flow duration'},
{id:'FL-0268',source:'192.168.1.11',destination:'10.0.0.4',port:53,label:'Normal',reason:'Illustrative DNS exchange'}];
