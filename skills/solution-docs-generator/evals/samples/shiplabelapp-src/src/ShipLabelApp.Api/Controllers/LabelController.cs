using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using ShipLabelApp.Api.Services;

namespace ShipLabelApp.Api.Controllers;

[Authorize]
[ApiController]
[Route("api/[controller]")]
public class LabelController : ControllerBase
{
    private readonly ILabelService _labels;
    public LabelController(ILabelService labels) => _labels = labels;

    // GET api/label/documents - delivery notes with parcels to label (view ACM_VIEW_LABELS)
    [HttpGet("documents")]
    public async Task<IActionResult> Documents() => Ok(await _labels.GetDocumentsAsync());

    // POST api/label/print
    [HttpPost("print")]
    public async Task<IActionResult> Print([FromBody] PrintRequest request)
    {
        if (request.ParcelIds.Count > _labels.MaxLabelsPerRequest)
            return BadRequest(new { message = $"Troppe etichette (massimo {_labels.MaxLabelsPerRequest} per stampa)" });

        var result = await _labels.PrintAsync(User.Identity!.Name!, request.ParcelIds);
        // NOTE: Queued is true also when the user has no printer configured (see LabelService)
        return Ok(new { message = "Etichetta inviata alla stampante", queued = result.Queued });
    }
}
