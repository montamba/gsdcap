
let API = {
    async sendData(url, data={}, method="GET"){
        let resdata
        
        if(method == "GET"){
            resdata = await fetch(url)
        }else if(method=="DELETE"){
            resdata = await fetch(url, {"method":method})
        }
        else{
            resdata = await fetch(url, {
                "method":method,
                headers: {'Content-Type': 'application/json'},
                body:JSON.stringify(data)
            })
        }

        let res = await resdata.json()

        return res;
    },
    login:(cred) => API.sendData("/auth/login",cred,"POST"),
    get:(url) => API.sendData(url),
    post:(url,data) => API.sendData(url,data,"POST"),
    put:(url,data) => API.sendData(url,data,"PUT"),
    delete:(url) => API.sendData(url,{},"DELETE"),

}


function showMessageModal(text,texttitle){
    let html = `
        <button class="messagex" commandfor="message-modal" command="close"><i class="bi bi-x-lg"></i></button>
        <div>
            <h1>${texttitle}</h1>
            <p>
            ${text}
            </p>
        </div>

    
    `
    let dialog = document.createElement("dialog");
    dialog.id = "message-modal"
    dialog.innerHTML = html

    document.body.prepend(dialog)
    dialog.showModal()



}