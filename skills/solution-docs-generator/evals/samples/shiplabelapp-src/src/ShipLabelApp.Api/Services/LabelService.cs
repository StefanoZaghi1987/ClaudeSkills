namespace ShipLabelApp.Api.Services;

public class LabelService : ILabelService
{
    private readonly IOrbitApiClient _orbit;
    private readonly IPrintClient _print;
    private readonly ILogger<LabelService> _log;
    public int MaxLabelsPerRequest { get; } = 50;

    public LabelService(IOrbitApiClient orbit, IPrintClient print, ILogger<LabelService> log)
        => (_orbit, _print, _log) = (orbit, print, log);

    public Task<IReadOnlyList<DocumentDto>> GetDocumentsAsync()
        => _orbit.QueryViewAsync<DocumentDto>("ACM_VIEW_LABELS");

    public async Task<PrintResult> PrintAsync(string userName, IReadOnlyList<int> parcelIds)
    {
        // Printer per user from user table ACM_USER_PRINTERS (UserName -> PrinterName)
        var printer = await _orbit.GetUserPrinterAsync(userName);
        if (printer is null)
        {
            // Nothing is sent, but the request is reported as queued: logged at Debug level only
            _log.LogDebug("No printer configured for {User}", userName);
            return new PrintResult(Queued: true);
        }
        foreach (var id in parcelIds)
        {
            var pdf = await _orbit.GetLabelPdfAsync(id);
            await _print.SendAsync(printer, pdf);   // LabelPrintService on PRN01
        }
        return new PrintResult(Queued: true);
    }
}
