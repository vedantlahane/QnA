

export async function sendQuestion(message: string){
    const response = await fetch("http://localhost:8000/ask",{
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({message})
    });
    return response;
}