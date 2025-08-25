-- ===============================================================
-- Subsidy Payment Process Logic
-- 2025.05.14   bindrap  Custom Implementation for 34032
-- ===============================================================

DECLARE @ResultCode INT;

SELECT @ResultCode = ResultCode
FROM FolderProcessAttempt
WHERE ProcessRSN = @ProcessRSN AND AttemptRSN = @AttemptRSN;

-- ===================
-- RESULT CODE 1 - APPROVED (AP Stamped Completed on Miro)
-- ===================
IF @ResultCode = 1
BEGIN
    -- Auto assign to 'Permit Clerk' handled by default assignment setup

    -- Update Process Status to Open
    EXEC dbo.cp_UpdateFolderProcess 
        @ProcessRSN = @ProcessRSN, 
        @StatusCode = 1; -- Open

    -- Update Folder Status to 'Approved for Payment'
    EXEC dbo.cp_UpdateFolder 
        @FolderRSN = @FolderRSN, 
        @StatusCode = 66051; -- Approved for Payment

    -- Send optional notification (if required)
    -- EXEC dbo.Send_Templated_Mail_Folder <TemplateID>, @FolderRSN, NULL, NULL, NULL, NULL, NULL;
END

-- ===================
-- RESULT CODE 275 - FINAL PAYMENT (Payment Completed on Miro)
-- ===================
IF @ResultCode = 275
BEGIN
    -- Auto assign to 'Permit Clerk' handled by default assignment setup

    -- Update Process Status to Closed
    EXEC dbo.cp_UpdateFolderProcess 
        @ProcessRSN = @ProcessRSN, 
        @StatusCode = 2; -- Closed

    -- Update Folder Status to 'Completed'
    EXEC dbo.cp_UpdateFolder 
        @FolderRSN = @FolderRSN, 
        @StatusCode = 2010; -- Completed

    -- Optionally: Insert Control Group InfoCode (if required for bulk upload)
    -- INSERT INTO FolderProcessInfo (FolderRSN, ProcessRSN, InfoCode, InfoValue, StampDate, StampUser)
    -- VALUES (@FolderRSN, @ProcessRSN, <ControlGroupCode>, 'SomeValue', GETDATE(), SYSTEM_USER);

    -- Optionally: Notification logic or update to 'Payment Issued' can go here if scheduled after 8 weeks
END